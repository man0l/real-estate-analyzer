import { Property } from '@/types/property';
import ImageSlider from './ImageSlider';

interface PropertyCardProps {
  property: Property;
}

export default function PropertyCard({ property }: PropertyCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <ImageSlider images={property.images.map(img => img.url)} />
      
      <div className="p-4">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold">{property.type}</h3>
            <p className="text-gray-600">
              {property.area_m2} m² • {property.floor_info?.current_floor}/{property.floor_info?.total_floors} floor
            </p>
          </div>
          <div className="text-right">
            <p className="text-xl font-bold">{property.price_value.toLocaleString()} {property.price_currency}</p>
            <p className="text-sm text-gray-500">
              {property.includes_vat ? 'Including VAT' : 'Excluding VAT'}
            </p>
          </div>
        </div>

        {property.construction_info && (
          <p className="text-sm text-gray-600 mb-2">
            Built: {property.construction_info.year} • {property.construction_info.type}
            {property.construction_info.has_central_heating && ' • Central Heating'}
          </p>
        )}

        {property.features.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {property.features.map((feature, index) => (
              <span key={index} className="text-xs bg-gray-100 rounded px-2 py-1">
                {feature}
              </span>
            ))}
          </div>
        )}

        {property.contact_info?.broker_name && (
          <div className="mt-4 pt-4 border-t">
            <p className="text-sm font-semibold">Broker: {property.contact_info.broker_name}</p>
            {property.contact_info.phone && (
              <p className="text-sm text-gray-600">{property.contact_info.phone}</p>
            )}
          </div>
        )}

        {property.monthly_payment && (
          <div className="mt-4 bg-blue-50 p-3 rounded-md">
            <p className="text-sm text-blue-800">
              Monthly payment: {property.monthly_payment.value} {property.monthly_payment.currency}
            </p>
          </div>
        )}

        <div className="mt-4 text-xs text-gray-500">
          <p>Last modified: {property.last_modified}</p>
          {property.views && <p>Views: {property.views}</p>}
        </div>
      </div>
    </div>
  );
} 