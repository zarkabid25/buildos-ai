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
