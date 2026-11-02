import { z } from 'zod';

export const itemSchema = z.object({
  title: z.string().min(3, 'Use at least 3 characters.').max(80, 'Use at most 80 characters.'),
  color: z.enum(['red', 'blue'], { error: 'Choose red or blue.' }),
  notes: z.string().min(1, 'Keep the existing note.').max(300, 'Use at most 300 characters.'),
});

export const initialDocument = {
  item: { id: 'sample-item', title: 'Weekly plan', color: 'blue',
    notes: 'Keep this existing note.\nSecond line: café ☕.', extra: { retained: 'Keep this item property.' } },
  settings: { density: 'comfortable', retained: 'Keep this setting.' },
  revision: 0,
};
