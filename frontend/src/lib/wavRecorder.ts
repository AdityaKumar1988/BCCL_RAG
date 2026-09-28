/**
 * Utility for in-browser microphone recording with direct 16-bit PCM WAV encoding.
 * Produces clean 16kHz mono WAV audio suitable for Python soundfile and OpenAI Whisper
 * without requiring external ffmpeg binaries on the host system.
 */

export class WavRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private audioBuffers: Float32Array[] = [];
  private recordingLength = 0;
  private sampleRate = 16000;

  private muteNode: GainNode | null = null;

  async start(): Promise<void> {
    if (!navigator?.mediaDevices?.getUserMedia) {
      throw new Error('Microphone access is not supported by your browser.');
    }

    this.audioBuffers = [];
    this.recordingLength = 0;

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    const AudioContextClass =
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;

    this.audioContext = new AudioContextClass({ sampleRate: 16000 });
    // Resume audio context if created in suspended state by browser policy
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
    this.sampleRate = this.audioContext.sampleRate || 16000;

    this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
    // Buffer size 4096, 1 input channel, 1 output channel
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e: AudioProcessingEvent) => {
      const channel = e.inputBuffer.getChannelData(0);
      this.audioBuffers.push(new Float32Array(channel));
      this.recordingLength += channel.length;
    };

    // Route processor to a muted gain node instead of raw speakers (destination)
    // to prevent acoustic feedback loop and aggressive browser echo-cancellation muting
    this.muteNode = this.audioContext.createGain();
    this.muteNode.gain.setValueAtTime(0, this.audioContext.currentTime);

    this.source.connect(this.processor);
    this.processor.connect(this.muteNode);
    this.muteNode.connect(this.audioContext.destination);
  }

  stop(): Blob {
    this.cleanupNodes();

    if (this.recordingLength === 0) {
      throw new Error('No audio captured. Please speak into your microphone.');
    }

    // Merge audio chunks into a single Float32Array
    const merged = new Float32Array(this.recordingLength);
    let offset = 0;
    for (const buf of this.audioBuffers) {
      merged.set(buf, offset);
      offset += buf.length;
    }

    this.audioBuffers = [];
    this.recordingLength = 0;

    return encodeWav(merged, this.sampleRate);
  }

  cancel(): void {
    this.cleanupNodes();
    this.audioBuffers = [];
    this.recordingLength = 0;
  }

  private cleanupNodes(): void {
    if (this.processor && this.source) {
      try {
        this.source.disconnect();
        this.processor.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      this.source = null;
      this.processor = null;
    }

    if (this.muteNode) {
      try {
        this.muteNode.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      this.muteNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch {
        // Ignore close errors
      }
      this.audioContext = null;
    }
  }
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');

  // "fmt " sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, 1, true); // NumChannels (1 = Mono)
  view.setUint32(24, sampleRate, true); // SampleRate
  view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
  view.setUint16(32, 2, true); // BlockAlign (NumChannels * BitsPerSample/8)
  view.setUint16(34, 16, true); // BitsPerSample (16 bits)

  // "data" sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Write PCM float samples as 16-bit signed integers
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}
