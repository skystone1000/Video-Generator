import { Heart, PlayCircle } from "lucide-react";

import { assetThumbnailUrl } from "../api/client";
import type { Asset } from "../api/types";

interface AssetGalleryProps {
  assets: Asset[];
  selectedAssetId: number | null;
  onSelect: (assetId: number) => void;
  onFavorite: (asset: Asset) => void;
}

export function AssetGallery({ assets, selectedAssetId, onSelect, onFavorite }: AssetGalleryProps) {
  return (
    <section className="galleryBand">
      <div className="galleryHeader">
        <h2>Assets</h2>
        <span>{assets.length} local outputs</span>
      </div>
      <div className="assetGrid">
        {assets.length === 0 ? <div className="quietText">Completed outputs appear here</div> : null}
        {assets.map((asset) => (
          <div
            key={asset.id}
            className={`assetTile ${selectedAssetId === asset.id ? "selected" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(asset.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") onSelect(asset.id);
            }}
          >
            <div className="thumb">
              {asset.thumbnail_path ? (
                <img src={assetThumbnailUrl(asset.id)} alt="" />
              ) : (
                <PlayCircle size={34} />
              )}
            </div>
            <div className="assetMeta">
              <span>Job #{asset.job_id}</span>
              <button
                type="button"
                className={asset.favorite ? "favorite active" : "favorite"}
                title="Favorite"
                onClick={(event) => {
                  event.stopPropagation();
                  onFavorite(asset);
                }}
              >
                <Heart size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
