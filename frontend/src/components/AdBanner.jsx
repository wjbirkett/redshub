/**
 * AdBanner — Google AdSense ad slot placeholder.
 * Set VITE_ADSENSE_CLIENT in .env to enable.
 */
import { useEffect } from "react";

export default function AdBanner({ style = {}, format = "auto" }) {
  const client = import.meta.env.VITE_ADSENSE_CLIENT;

  useEffect(() => {
    if (client && window.adsbygoogle) {
      try {
        window.adsbygoogle.push({});
      } catch (e) {}
    }
  }, [client]);

  if (!client) return null;

  return (
    <ins
      className="adsbygoogle"
      style={{ display: "block", textAlign: "center", ...style }}
      data-ad-client={client}
      data-ad-slot="auto"
      data-ad-format={format}
      data-full-width-responsive="true"
    />
  );
}
