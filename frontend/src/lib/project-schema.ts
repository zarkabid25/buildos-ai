import { z } from "zod";

export const projectCreateSchema = z.object({
  name: z.string().min(2, "Project name is required"),
  code: z.string().min(1, "Project code is required").max(50),
  client_name: z.string().optional(),
  location: z.string().optional(),
  project_type: z.string().optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  budget: z.string().optional(),
});
export type ProjectCreateInput = z.infer<typeof projectCreateSchema>;
