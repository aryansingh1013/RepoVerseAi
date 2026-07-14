import { SpaceScene } from "@/three/SpaceScene";
import { NavigationHud } from "@/components/layout/NavigationHud";

export function Workspace() {
  return (
    <div className="absolute inset-0">
      <SpaceScene />
      <NavigationHud />
    </div>
  );
}
