"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { zoneUpdateSchema, type ZoneUpdateFormValues } from "@/lib/validations/zone";
import type { Zone } from "@/types/zone";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/authStore";

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

interface Props {
  zone: Zone;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditZoneDialog({ zone, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdmin = user?.is_admin;
  
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [newOwnerId, setNewOwnerId] = useState("");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ZoneUpdateFormValues>({
    resolver: zodResolver(zoneUpdateSchema as any),
    defaultValues: {
      zone_name: zone.zone_name ?? zone.name,
      soil_type: zone.soil_type,
      crop_type: zone.crop_type,
      moisture_min: zone.moisture_min,
      moisture_max: zone.moisture_max,
      active: zone.active ?? zone.is_active,
    },
  });

  const isActive = watch("active");
  const soilType = watch("soil_type");

  const isSystemZone = zone.source === "yaml" && !zone.owner_id;
  const canModify = isAdmin || !isSystemZone;

  const updateMutation = useMutation({
    mutationFn: (data: ZoneUpdateFormValues) => api.put(`/v1/zones/${zone.zone_id ?? zone.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      toast.success("Zone updated successfully");
      onOpenChange(false);
    },
    onError: () => toast.error("Failed to update zone"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/v1/zones/${zone.zone_id ?? zone.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      toast.success("Zone deleted");
      setDeleteOpen(false);
      onOpenChange(false);
    },
    onError: () => toast.error("Failed to delete zone"),
  });

  const assignMutation = useMutation({
    mutationFn: (owner_id: string) => api.post(`/v1/zones/${zone.zone_id ?? zone.id}/assign`, { owner_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      toast.success("Zone reassigned successfully");
    },
    onError: () => toast.error("Failed to reassign zone"),
  });

  const onSubmit = (data: ZoneUpdateFormValues) => {
    updateMutation.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Edit Zone Configuration</DialogTitle>
          <DialogDescription>
            Update properties and moisture thresholds for this zone.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2 col-span-2">
              <Label htmlFor="zone_name">Zone Name</Label>
              <Input
                id="zone_name"
                {...register("zone_name")}
                disabled={!canModify}
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
                disabled={!canModify}
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
                {...register("crop_type")}
                disabled={!canModify}
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
                disabled={!canModify}
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
                disabled={!canModify}
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
              disabled={!canModify}
            />
            <Label htmlFor="active">Zone is active</Label>
          </div>

          {isAdmin && (
            <div className="pt-4 border-t border-border mt-4">
              <Label className="text-xs uppercase text-muted-foreground mb-2 block">Danger Zone (Admin)</Label>
              <div className="flex gap-2">
                <Input 
                  placeholder="New Owner UUID" 
                  value={newOwnerId}
                  onChange={(e) => setNewOwnerId(e.target.value)}
                  className="text-xs"
                />
                <Button 
                  type="button" 
                  variant="secondary"
                  disabled={!newOwnerId || assignMutation.isPending}
                  onClick={() => assignMutation.mutate(newOwnerId)}
                >
                  Assign
                </Button>
              </div>
            </div>
          )}

          <div className="flex justify-between gap-2 pt-4 border-t border-border mt-4">
            <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
              <AlertDialogTrigger
                render={
                  <Button 
                    type="button" 
                    variant="destructive" 
                    size="icon" 
                    disabled={!canModify}
                    title={!canModify ? "System-defined zones cannot be deleted" : "Delete zone"}
                  >
                    <Trash2 size={16} />
                  </Button>
                }
              />
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete this zone and all associated sensor data and irrigation events. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.preventDefault();
                      deleteMutation.mutate();
                    }}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {deleteMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Delete"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <div className="flex gap-2">
              <Button variant="outline" type="button" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending || !canModify}>
                {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
