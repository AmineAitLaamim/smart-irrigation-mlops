"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { zoneSchema, type ZoneFormValues } from "@/lib/validations/zone";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Plus, Loader2 } from "lucide-react";

const SOIL_TYPES = [
  { value: "clay", label: "Clay" },
  { value: "sandy_loam", label: "Sandy Loam" },
  { value: "loam", label: "Loam" },
  { value: "clay_loam", label: "Clay Loam" },
  { value: "silt", label: "Silt" },
  { value: "sand", label: "Sand" },
  { value: "silty_loam", label: "Silty Loam" },
  { value: "peat", label: "Peat" },
];

export function CreateZoneDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<ZoneFormValues>({
    resolver: zodResolver(zoneSchema as any),
    defaultValues: {
      active: true,
      moisture_min: 20,
      moisture_max: 60,
      soil_type: "loam",
    },
  });

  const isActive = watch("active");
  const soilType = watch("soil_type");

  const mutation = useMutation({
    mutationFn: (data: ZoneFormValues) => api.post("/v1/zones", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      setOpen(false);
      reset();
    },
  });

  const onSubmit = (data: ZoneFormValues) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button className="gap-2">
            <Plus size={18} />
            Add Zone
          </Button>
        }
      />
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create Irrigation Zone</DialogTitle>
          <DialogDescription>
            Add a new zone to monitor and control its irrigation schedule.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2 col-span-2">
              <Label htmlFor="zone_name">Zone Name</Label>
              <Input
                id="zone_name"
                placeholder="e.g. North Garden"
                {...register("zone_name")}
              />
              {errors.zone_name && (
                <p className="text-xs text-destructive">{errors.zone_name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="soil_type">Soil Type</Label>
              <Select
                value={soilType}
                onValueChange={(value) => setValue("soil_type", value ?? "")}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select soil type" />
                </SelectTrigger>
                <SelectContent>
                  {SOIL_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.soil_type && (
                <p className="text-xs text-destructive">{errors.soil_type.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="crop_type">Crop Type</Label>
              <Input
                id="crop_type"
                placeholder="e.g. Tomatoes"
                {...register("crop_type")}
              />
              {errors.crop_type && (
                <p className="text-xs text-destructive">{errors.crop_type.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="moisture_min">Min Moisture (%)</Label>
              <Input
                id="moisture_min"
                type="number"
                {...register("moisture_min")}
              />
              {errors.moisture_min && (
                <p className="text-xs text-destructive">{errors.moisture_min.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="moisture_max">Max Moisture (%)</Label>
              <Input
                id="moisture_max"
                type="number"
                {...register("moisture_max")}
              />
              {errors.moisture_max && (
                <p className="text-xs text-destructive">{errors.moisture_max.message}</p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2 pt-2">
            <Switch
              id="active"
              checked={isActive}
              onCheckedChange={(checked) => setValue("active", checked)}
            />
            <Label htmlFor="active">Zone is active</Label>
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive font-medium">
              {mutation.error instanceof Error ? mutation.error.message : "Failed to create zone. Please try again."}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" type="button" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Zone
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
