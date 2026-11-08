"use client";

import { useEffect, useRef } from "react";

type Props = React.ComponentPropsWithoutRef<"video">;

function lockSilent(node: HTMLVideoElement) {
  node.muted = true;
  node.volume = 0;
}

/** Exercise clips stay silent, including after the viewer taps the speaker control. */
export default function SilentVideo({ onVolumeChange, ...props }: Props) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (node) lockSilent(node);
  });

  return (
    <video
      {...props}
      ref={ref}
      muted
      onVolumeChange={(event) => {
        lockSilent(event.currentTarget);
        onVolumeChange?.(event);
      }}
    />
  );
}
