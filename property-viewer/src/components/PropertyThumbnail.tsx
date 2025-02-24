import { Property } from '@/types/property';
import Image from 'next/image';

interface PropertyThumbnailProps {
  property: Property;
  onClick: () => void;
}

export default function PropertyThumbnail({ property, onClick }: PropertyThumbnailProps) {
  const mainImage = property.images[0]?.url;
  
  return (
    <div 
      className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow duration-200"
      onClick={onClick}
    >
      <div className="relative aspect-[4/3] w-full">
        {mainImage ? (
          <Image
            src={mainImage}
            alt={property.type}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-cover"
            priority
          />
        ) : (
          <div className="h-full w-full bg-gray-200 flex items-center justify-center">
            <span className="text-gray-400">No image</span>
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
          <p className="text-white font-semibold">{property.price_value.toLocaleString()} {property.price_currency}</p>
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
      </div>
    </div>
  );
} 