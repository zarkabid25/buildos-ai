import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  company_name: z.string().min(2, "Company name is required"),
  company_code: z
    .string()
    .min(2, "Company code is required")
    .max(50)
    .regex(/^[a-zA-Z0-9-]+$/, "Letters, numbers and dashes only"),
  full_name: z.string().min(2, "Your name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
});
export type RegisterInput = z.infer<typeof registerSchema>;

export const acceptInviteSchema = z
  .object({
    full_name: z.string().trim().min(2, "Your name is required").max(255),
    password: z.string().min(8, "At least 8 characters").max(128),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { message: "Passwords don't match", path: ["confirm"] });
export type AcceptInviteInput = z.infer<typeof acceptInviteSchema>;

export const inviteSchema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  full_name: z.string().trim().max(255).optional(),
  role: z.enum(["company_admin", "project_manager", "site_engineer", "storekeeper", "accountant", "viewer", "super_admin"]),
});
export type InviteInput = z.infer<typeof inviteSchema>;
