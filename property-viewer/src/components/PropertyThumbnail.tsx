import { Property } from '@/types/property';
import Image from 'next/image';
import { useMemo } from 'react';

interface PropertyThumbnailProps {
  property: Property;
  onClick: () => void;
}

export default function PropertyThumbnail({ property, onClick }: PropertyThumbnailProps) {
  const mainImage = property.images[0];
  const imageUrl = mainImage ? (mainImage.storage_url || mainImage.url) : null;
  const constructionInfo = property.construction_info;
  
  // Format the planned date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('bg-BG', { month: 'long', year: 'numeric' });
  };

  // Format price with consistent output
  const formattedPrice = useMemo(() => {
    if (property.price_value == null) return 'Price not available';
    
    // Format number with consistent thousand separators
    const numberStr = property.price_value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return `${numberStr} ${property.price_currency}`;
  }, [property.price_value, property.price_currency]);

  // Check if we have a valid image URL
  const hasValidImageUrl = imageUrl && imageUrl.trim().length > 0;
  
  return (
    <div 
      className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow duration-200"
      onClick={onClick}
    >
      <div className="relative aspect-[4/3] w-full">
        {hasValidImageUrl ? (
          <Image
            src={imageUrl}
            alt={property.type || 'Property image'}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-cover"
            priority
          />
        ) : (
          <div className="h-full w-full bg-gray-200 flex items-center justify-center">
            <p className="text-gray-500">No image available</p>
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
          <p className="text-white font-semibold">{formattedPrice}</p>
          {property.price_value && property.area_m2 && (
            <p className="text-white text-sm opacity-90">
              {Math.round(property.price_value / property.area_m2).toLocaleString()} {property.price_currency}/m²
            </p>
          )}
        </div>
      </div>
      
      <div className="p-4">
        <h3 className="font-semibold text-gray-800 mb-1">{property.type}</h3>
        <div className="flex items-center text-sm text-gray-600 gap-2">
          <span>{property.area_m2} m²</span>
          {property.floor_info && (
            <>
              <span>•</span>
              <span>Floor {property.floor_info.current_floor}/{property.floor_info.total_floors}</span>
            </>
          )}
        </div>
        {property.location?.district && (
          <p className="text-sm text-gray-500 mt-1">{property.location.district}</p>
        )}
        
        {/* Property status badges */}
        <div className="flex flex-wrap gap-1 mt-2">
          {/* Act 16 status badge */}
          {constructionInfo?.has_act16 !== null && constructionInfo?.has_act16 !== undefined && (
            <span className={`px-2 py-0.5 text-xs rounded-full ${
              constructionInfo.has_act16
                ? 'bg-green-100 text-green-800'
                : 'bg-orange-100 text-orange-800'
            }`}>
              {constructionInfo.has_act16 ? 'Act 16' : 'Under Construction'}
            </span>
          )}

          {/* Planned completion date badge */}
          {!constructionInfo?.has_act16 && constructionInfo?.act16_plan_date && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
              Ready: {formatDate(constructionInfo.act16_plan_date)}
            </span>
          )}

          {/* Renovation status badge */}
          {constructionInfo?.is_renovated !== null && constructionInfo?.is_renovated !== undefined && (
            <span className={`px-2 py-0.5 text-xs rounded-full ${
              constructionInfo.is_renovated
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {constructionInfo.is_renovated ? 'Renovated' : 'Needs Renovation'}
            </span>
          )}

          {/* Furnishing status badge */}
          {constructionInfo?.is_furnished !== null && constructionInfo?.is_furnished !== undefined && (
            <span className={`px-2 py-0.5 text-xs rounded-full ${
              constructionInfo.is_furnished
                ? 'bg-blue-100 text-blue-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {constructionInfo.is_furnished ? 'Furnished' : 'Unfurnished'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
} 