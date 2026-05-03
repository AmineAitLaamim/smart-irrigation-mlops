export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">Configure your system and preferences.</p>
      </div>

      <div className="grid gap-6">
        <div className="bg-secondary/50 rounded-xl p-12 flex items-center justify-center border-2 border-dashed border-border text-center">
          <div>
            <p className="text-muted-foreground font-medium text-lg">System Configuration</p>
            <p className="text-sm text-muted-foreground mt-2">Centralized settings coming in the next update.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
