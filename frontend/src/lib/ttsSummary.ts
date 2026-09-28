/**
 * Lightweight, deterministic client-side extraction of key points and concise spoken summaries
 * from official BCCL assistant answers for browser Text-to-Speech (TTS).
 * 
 * Rules:
 * - Does NOT add new facts.
 * - Does NOT make the summary more specific than the original answer.
 * - Does NOT reinterpret legal rules.
 * - If the answer is an abstention, reads the exact abstention message.
 * - Stays 100% faithful to the displayed answer text.
 */
export function extractKeyPointsSummary(content: string): string {
  if (!content || !content.trim()) return '';

  const trimmed = content.trim();

  // 1. Abstention check
  if (
    trimmed.toLowerCase().includes('could not find sufficient information') ||
    trimmed.toLowerCase().includes('information is not available')
  ) {
    return 'I could not find sufficient information about this in the available BCCL documents.';
  }

  // 2. Short conversational messages (greetings, goodbyes, one-liners)
  if (trimmed.length < 180 && !trimmed.includes('\n-') && !trimmed.includes('\n*')) {
    return trimmed.replace(/[#*`_]/g, '').trim();
  }

  // 3. Extract rule number if present (e.g. Rule 26, Rule 27, Rule 5, Rule 29, Rule 34)
  const ruleMatch = trimmed.match(/\bRule\s+\d+(\.\d+)?\b/i);
  const ruleMention = ruleMatch ? ruleMatch[0] : '';

  // 4. Extract lines and separate header, intro statement, and bullets
  const lines = trimmed.split('\n');
  const bullets: { title: string; text: string }[] = [];
  let header = '';
  let introStatement = '';

  for (const line of lines) {
    const clean = line.trim();
    if (!clean) continue;

    if (clean.startsWith('#')) {
      if (!header && !clean.toLowerCase().includes('relevant rule')) {
        header = clean.replace(/^[#\s]+/, '').replace(/[*`_]/g, '').trim();
      }
      continue;
    }

    if (/^[-*•]\s+/.test(clean) || /^\d+\.\s+/.test(clean)) {
      let item = clean.replace(/^[-*•\d.]+\s+/, '').trim();
      item = item.replace(/\*\*(.*?)\*\*/g, '$1').replace(/[*`_]/g, '').trim();
      if (!item) continue;

      // Check if bullet has a sub-heading like "Title: details..."
      const colonIdx = item.indexOf(':');
      if (colonIdx > 0 && colonIdx < 45) {
        const title = item.slice(0, colonIdx).trim();
        const desc = item.slice(colonIdx + 1).trim();
        let firstSentence = desc.split(/(?<=[.?!])\s+/)[0];
        if (firstSentence.length > 140) {
          const commaIdx = firstSentence.indexOf(',', 40);
          if (commaIdx > 35 && commaIdx < 130) {
            firstSentence = firstSentence.slice(0, commaIdx);
          } else {
            firstSentence = firstSentence.slice(0, 130);
          }
        }
        firstSentence = firstSentence.replace(/\s+(plus|and|or|with|to|of|for|in|under|by)$/i, '');
        bullets.push({ title, text: firstSentence.replace(/[.;,]+$/, '') });
      } else {
        let firstSentence = item.split(/(?<=[.?!])\s+/)[0];
        if (firstSentence.length > 140) {
          const commaIdx = firstSentence.indexOf(',', 40);
          if (commaIdx > 35 && commaIdx < 130) {
            firstSentence = firstSentence.slice(0, commaIdx);
          } else {
            firstSentence = firstSentence.slice(0, 130);
          }
        }
        firstSentence = firstSentence.replace(/\s+(plus|and|or|with|to|of|for|in|under|by)$/i, '');
        bullets.push({ title: '', text: firstSentence.replace(/[.;,]+$/, '') });
      }
    } else if (!introStatement && bullets.length === 0 && !clean.toLowerCase().includes('relevant rule') && !clean.startsWith('[')) {
      const cleanIntro = clean.replace(/\*\*(.*?)\*\*/g, '$1').replace(/[*`_]/g, '').trim();
      if (cleanIntro.length > 10) {
        introStatement = cleanIntro.replace(/:\s*$/, '');
      }
    }
  }

  // 5. Build summary from structured components
  if (bullets.length > 0) {
    // Check if bullets are short item names (e.g. list of penalties or charges)
    const isItemList = bullets.every((b) => !b.title && b.text.split(' ').length <= 6);

    if (isItemList) {
      const items = bullets.slice(0, 5).map((b) => b.text.toLowerCase());
      const formattedItems =
        items.length > 1
          ? items.slice(0, -1).join(', ') + ', and ' + items[items.length - 1]
          : items[0];

      if (introStatement) {
        return `${introStatement}: ${formattedItems}.`.replace(/\s+/g, ' ').trim();
      }
      if (ruleMention && header) {
        return `Under ${ruleMention}, ${header.toLowerCase()} include ${formattedItems}.`.replace(/\s+/g, ' ').trim();
      }
      if (header) {
        return `${header} include ${formattedItems}.`.replace(/\s+/g, ' ').trim();
      }
      return `Key points include ${formattedItems}.`.replace(/\s+/g, ' ').trim();
    }

    // Bullets with descriptions or titles (e.g. suspension provisions)
    const topBullets = bullets.slice(0, 3);
    const spokenBullets = topBullets
      .map((b) => {
        if (b.title) {
          return `${b.title}: ${b.text}.`;
        }
        return `${b.text}.`;
      })
      .join(' ');

    let lead = '';
    if (ruleMention && header) {
      lead = `Under ${ruleMention} regarding ${header}: `;
    } else if (introStatement) {
      lead = `${introStatement}. `;
    } else if (ruleMention) {
      lead = `Under ${ruleMention}: `;
    } else if (header) {
      lead = `Regarding ${header}: `;
    }

    return `${lead}${spokenBullets}`.replace(/\s+/g, ' ').trim();
  }

  // 6. Fallback: Normal paragraph answer without bullets
  const cleanBody = trimmed
    .replace(/^#+.*$/gm, '')
    .replace(/\[Source:[^\]]+\]/g, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/[*`_]/g, '')
    .trim();

  const sentences = cleanBody.split(/(?<=[.?!])\s+/).filter((s) => s.trim().length > 15);
  if (sentences.length > 0) {
    return sentences.slice(0, 2).join(' ').trim();
  }

  return cleanBody.slice(0, 200).trim();
}
