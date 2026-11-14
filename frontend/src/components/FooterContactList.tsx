"use client";

import { useEffect, useState } from "react";
import {
  CONTACT_EMAIL,
  CONTACT_FACEBOOK_DISPLAY,
  CONTACT_PHONE_DISPLAY,
  CONTACT_TIKTOK_DISPLAY,
} from "@/lib/brand";
import { SITE_PAGE_MEDIA_DEFAULTS, fetchSitePageMedia } from "@/lib/sitePageMedia";

const ITEMS = [
  { key: "footer_phone_href", label: `SĐT: ${CONTACT_PHONE_DISPLAY}` },
  { key: "footer_email_href", label: `Email: ${CONTACT_EMAIL}` },
  { key: "footer_facebook_href", label: `Facebook: ${CONTACT_FACEBOOK_DISPLAY}` },
  { key: "footer_tiktok_href", label: `TikTok: ${CONTACT_TIKTOK_DISPLAY}` },
] as const;

function opensNewTab(href: string) {
  return href.startsWith("http://") || href.startsWith("https://");
}

export default function FooterContactList() {
  const [links, setLinks] = useState({
    footer_phone_href: SITE_PAGE_MEDIA_DEFAULTS.footer_phone_href,
    footer_email_href: SITE_PAGE_MEDIA_DEFAULTS.footer_email_href,
    footer_facebook_href: SITE_PAGE_MEDIA_DEFAULTS.footer_facebook_href,
    footer_tiktok_href: SITE_PAGE_MEDIA_DEFAULTS.footer_tiktok_href,
  });

  useEffect(() => {
    let live = true;
    void fetchSitePageMedia().then((media) => {
      if (!live) return;
      setLinks({
        footer_phone_href: media.footer_phone_href,
        footer_email_href: media.footer_email_href,
        footer_facebook_href: media.footer_facebook_href,
        footer_tiktok_href: media.footer_tiktok_href,
      });
    });
    return () => {
      live = false;
    };
  }, []);

  return (
    <ul className="mt-3 space-y-2 text-sm text-slate-400">
      {ITEMS.map((item) => {
        const href = links[item.key];
        const external = opensNewTab(href);
        return (
          <li key={item.key}>
            <a
              href={href}
              {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              className="transition hover:text-brand-400"
            >
              {item.label}
            </a>
          </li>
        );
      })}
    </ul>
  );
}
