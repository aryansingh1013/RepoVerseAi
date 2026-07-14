import { AppShell } from "@/components/layout/AppShell";
import { SpaceScene } from "@/three/SpaceScene";
import { NavigationHud } from "@/components/layout/NavigationHud";
import { useNavigation } from "@/hooks/useNavigation";
import { useEffect } from "react";

export function WorkspacePage() {
  const { refreshScan } = useNavigation();

  useEffect(() => {
    refreshScan();
  }, [refreshScan]);

  return (
    <AppShell>
      <div className="absolute inset-0 z-0">
        <SpaceScene />
        <NavigationHud />
      </div>
    </AppShell>
  );
}
