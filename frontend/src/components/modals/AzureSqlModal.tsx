import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import type { AzureSqlConfig } from "@/types";
import { loadAzureSqlConfig, saveAzureSqlConfig } from "@/lib/storage";
import { useEffect, useState } from "react";

interface AzureSqlModalProps {
  open: boolean;
  onClose: () => void;
}

const EMPTY: AzureSqlConfig = {
  server: "",
  database: "",
  username: "",
  password: "",
};

export function AzureSqlModal({ open, onClose }: AzureSqlModalProps) {
  const [form, setForm] = useState<AzureSqlConfig>(EMPTY);
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    if (open) {
      setForm(loadAzureSqlConfig());
      setStatus("");
    }
  }, [open]);

  function update<K extends keyof AzureSqlConfig>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSave() {
    if (!form.server || !form.database || !form.username || !form.password) {
      setStatus("Fill in Server, Database, Username, and Password.");
      return;
    }
    saveAzureSqlConfig(form);
    setStatus("Saved locally. Open Data Sources to connect.");
  }

  return (
    <Modal open={open} onClose={onClose} title="Connect Azure SQL" wide>
      <p className="mb-4 text-sm text-zinc-400">
        Store connection details for any Azure SQL instance. Credentials stay in
        this browser only and are never hardcoded in the app.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-zinc-400" htmlFor="sql-server">
            Server
          </label>
          <Input
            id="sql-server"
            value={form.server}
            onChange={(event) => update("server", event.target.value)}
            placeholder="your-server.database.windows.net"
            autoComplete="off"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-400" htmlFor="sql-db">
            Database
          </label>
          <Input
            id="sql-db"
            value={form.database}
            onChange={(event) => update("database", event.target.value)}
            placeholder="semiconductor_dw"
            autoComplete="off"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-400" htmlFor="sql-user">
            Username
          </label>
          <Input
            id="sql-user"
            value={form.username}
            onChange={(event) => update("username", event.target.value)}
            placeholder="sqladmin"
            autoComplete="username"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-zinc-400" htmlFor="sql-pass">
            Password
          </label>
          <Input
            id="sql-pass"
            type="password"
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </div>
      </div>

      {status && <p className="mt-3 text-xs text-zinc-400">{status}</p>}

      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button type="button" variant="accent" onClick={handleSave}>
          Save
        </Button>
      </div>
    </Modal>
  );
}
