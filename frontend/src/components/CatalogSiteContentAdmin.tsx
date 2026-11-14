"use client";

import { useState } from "react";
import CatalogLegalAdmin from "./CatalogLegalAdmin";
import CatalogSitePageMediaAdmin from "./CatalogSitePageMediaAdmin";

export default function CatalogSiteContentAdmin() {
  const [pane, setPane] = useState<"media" | "legal">("media");

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Nội dung web</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className={
            pane === "media"
              ? "rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
              : "rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-600 ring-1 ring-slate-200"
          }
          onClick={() => setPane("media")}
        >
          Ảnh và video
        </button>
        <button
          type="button"
          className={
            pane === "legal"
              ? "rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
              : "rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-600 ring-1 ring-slate-200"
          }
          onClick={() => setPane("legal")}
        >
          Chính sách
        </button>
      </div>
      <div className="mt-6">
        {pane === "media" ? <CatalogSitePageMediaAdmin embedded /> : <CatalogLegalAdmin />}
      </div>
    </div>
  );
}
