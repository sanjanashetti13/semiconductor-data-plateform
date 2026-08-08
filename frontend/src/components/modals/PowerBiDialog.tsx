import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { loadPowerBiUrl, savePowerBiUrl } from "@/lib/storage";
import { useEffect, useState } from "react";

interface PowerBiDialogProps {
  open: boolean;
  onClose: () => void;
}

export function PowerBiDialog({ open, onClose }: PowerBiDialogProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setUrl(loadPowerBiUrl());
      setError("");
    }
  }, [open]);

  function handleSave() {
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Enter a valid Power BI dashboard URL.");
      return;
    }
    try {
      new URL(trimmed);
    } catch {
      setError("Enter a valid URL (https://...).");
      return;
    }
    savePowerBiUrl(trimmed);
    window.open(trimmed, "_blank", "noopener,noreferrer");
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title="Configure Power BI Dashboard URL">
      <p className="mb-4 text-sm text-zinc-400">
        Power BI is not recreated here. Paste your published dashboard URL to open
        it in a new tab.
      </p>
      <label className="mb-1 block text-xs font-medium text-zinc-400" htmlFor="pbi-url">
        Dashboard URL
      </label>
      <Input
        id="pbi-url"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="https://app.powerbi.com/..."
        autoFocus
      />
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="accent" onClick={handleSave}>
          Save & Open
        </Button>
      </div>
    </Modal>
  );
}
