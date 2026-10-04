import { useMemo, useState } from "react";
import { motion } from "framer-motion";

function normalizeImage(image) {
  if (!image) {
    return null;
  }

  if (typeof image === "string") {
    return image;
  }

  return image.image_url ?? image.url ?? image.image ?? null;
}

export default function ProductGallery({ images = [] }) {
  const fallback = "/placeholder.png";

  const gallery = useMemo(() => {
    const normalized = images.map(normalizeImage).filter(Boolean);

    return normalized.length > 0 ? normalized : [fallback];
  }, [images]);

  const [selectedImage, setSelectedImage] = useState(null);
  const selected = gallery.includes(selectedImage) ? selectedImage : gallery[0];

  return (
    <div className="flex gap-4 bg-[#232F3E] p-2">
      {/* Thumbnail gallery */}
      <div className="order-2 flex gap-3 overflow-x-auto lg:order-1 lg:w-24 lg:flex-col">
        {gallery.map((image, index) => (
          <button
            key={`${image}-${index}`}
            type="button"
            onClick={() => setSelectedImage(image)}
            className={`h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 bg-white transition ${
              selected === image
                ? "border-[#FFB703]"
                : "border-gray-200 hover:border-gray-400"
            }`}
          >
            <img
              src={image}
              alt={`Product view ${index + 1}`}
              className="h-full w-full object-contain p-2"
            />
          </button>
        ))}
      </div>

      {/* Main image */}
      <div className="group flex h-[500px] flex-1 items-center justify-center overflow-hidden rounded-xl bg-[#232F3E]">
        <motion.img
          key={selected}
          src={selected}
          alt="Product"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          whileHover={{ scale: 1.05 }}
          className="max-h-full max-w-full object-contain cursor-zoom-in"
          style={{
            filter: "brightness(1.25) saturate(1.15)",
          }}
        />
      </div>
    </div>
  );
}
