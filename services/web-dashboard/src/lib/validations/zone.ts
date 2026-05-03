import * as z from "zod";

export const zoneSchema = z.object({
  zone_id: z
    .string()
    .min(3, "Zone ID must be at least 3 characters")
    .max(50, "Zone ID must be less than 50 characters")
    .regex(/^[a-z0-9-]+$/, "Zone ID can only contain lowercase letters, numbers, and hyphens")
    .optional(),
  zone_name: z.string().min(1, "Zone Name is required"),
  soil_type: z.string().min(1, "Soil Type is required"),
  crop_type: z.string().min(1, "Crop Type is required"),
  moisture_min: z.coerce.number().min(0).max(100),
  moisture_max: z.coerce.number().min(0).max(100),
  active: z.boolean().default(true),
}).refine((data) => data.moisture_min < data.moisture_max, {
  message: "Minimum moisture must be less than maximum moisture",
  path: ["moisture_max"],
});

export type ZoneFormValues = z.infer<typeof zoneSchema>;

export const zoneUpdateSchema = z.object({
  zone_name: z.string().min(1, "Zone Name is required").optional(),
  soil_type: z.string().min(1, "Soil Type is required").optional(),
  crop_type: z.string().min(1, "Crop Type is required").optional(),
  moisture_min: z.coerce.number().min(0).max(100).optional(),
  moisture_max: z.coerce.number().min(0).max(100).optional(),
  active: z.boolean().optional(),
}).refine((data) => {
  if (data.moisture_min !== undefined && data.moisture_max !== undefined) {
    return data.moisture_min < data.moisture_max;
  }
  return true;
}, {
  message: "Minimum moisture must be less than maximum moisture",
  path: ["moisture_max"],
});

export type ZoneUpdateFormValues = z.infer<typeof zoneUpdateSchema>;
