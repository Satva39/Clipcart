import { useState } from "react";

export default function ProductShare({ product }) {
    const [copied, setCopied] = useState(false);

    async function handleShare() {
        const url = window.location.href;

        try {
            if (navigator.share) {
                await navigator.share({
                    title: product?.name || "Clipcart Product",
                    text: product?.description || "",
                    url,
                });
                return;
            }

            await navigator.clipboard.writeText(url);
            setCopied(true);

            setTimeout(() => {
                setCopied(false);
            }, 2000);
        } catch (error) {
            console.error("Share failed:", error);
        }
    }

    return (
        <button
            type="button"
            onClick={handleShare}
            className="rounded-xl bg-[#232F3E] px-6 py-3 font-bold transition hover:bg-[#2d3b4d]"
        >
            {copied ? "✓ Link Copied" : "🔗 Share Product"}
        </button>
    );
}