import { z } from 'zod';

export const emailSchema = z
  .string()
  .trim()
  .min(1, 'Email is required.')
  .email('Enter a valid email address.');

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters long.')
  .max(128, 'Password is too long.')
  .refine((value) => /[A-Za-z]/.test(value), {
    message: 'Password must include at least one letter.',
  })
  .refine((value) => /\d/.test(value), {
    message: 'Password must include at least one number.',
  });

export const assetCodeSchema = z
  .string()
  .trim()
  .min(1, 'Asset code is required.')
  .regex(/^[A-Za-z0-9][A-Za-z0-9-]*$/, 'Asset code can only contain letters, numbers, and hyphens.');

/** Pulls the asset code out of scanned QR text: a bare code, a `?code=` link, or a legacy `/verification/<code>/` link. */
export const extractAssetCode = (text: string): string => {
  const trimmed = text.trim();
  try {
    const url = new URL(trimmed);
    const fromQuery = url.searchParams.get('code');
    if (fromQuery) return fromQuery;
    const segments = url.pathname.split('/').filter(Boolean);
    return segments[segments.length - 1] ?? trimmed;
  } catch {
    return trimmed;
  }
};

export const incidentSchema = z.object({
  title: z.string().trim().min(5, 'Incident title must be at least 5 characters long.').max(120, 'Incident title is too long.'),
  assetId: z.string().trim().min(3, 'Asset ID is required.').max(80, 'Asset ID is too long.'),
  assetName: z.string().trim().min(2, 'Asset name is required.').max(120, 'Asset name is too long.'),
  ownerName: z.string().trim().min(2, 'Carrier name is required.').max(120, 'Carrier name is too long.'),
  universityId: z.string().trim().max(40, 'Student or staff ID is too long.').optional().or(z.literal('')),
  description: z.string().trim().min(10, 'Incident details must be at least 10 characters long.').max(1000, 'Incident details are too long.'),
});
