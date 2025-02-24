import { Property } from '@/types/property';
import ImageSlider from './ImageSlider';

interface PropertyCardProps {
  property: Property;
}

export default function PropertyCard({ property }: PropertyCardProps) {
  // Format price with consistent output
  const formattedPrice = property.price_value?.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ") || '0';

  // Get construction status
  const getConstructionStatus = () => {
    const info = property.construction_info;
    if (!info) return null;

    if (info.has_act16) {
      return { type: 'completed', text: 'With Act 16', details: info.act16_details };
    }

    if (info.act16_plan_date) {
      return {
        type: 'planned',
        text: `Act 16 planned: ${new Date(info.act16_plan_date).toLocaleDateString('bg-BG', { month: 'long', year: 'numeric' })}`,
        details: info.act16_details
      };
    }

    // Check description for Act status
    const description = property.description?.toLowerCase() || '';
    if (description.includes('акт 15') || description.includes('act 15')) {
      return { type: 'progress', text: 'Act 15', details: info.act16_details };
    } else if (description.includes('акт 14') || description.includes('act 14')) {
      return { type: 'progress', text: 'Act 14', details: info.act16_details };
    }

    return { type: 'progress', text: 'Under Construction', details: info.act16_details };
  };

  const constructionStatus = getConstructionStatus();

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <ImageSlider images={property.images} />
      
      <div className="p-4">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold">{property.type}</h3>
            <p className="text-gray-600">
              {property.area_m2} m² • {property.floor_info?.current_floor}/{property.floor_info?.total_floors} floor
            </p>
          </div>
          <div className="text-right">
            <p className="text-xl font-bold">{formattedPrice} {property.price_currency}</p>
            <p className="text-sm text-gray-500">
              {property.includes_vat ? 'Including VAT' : 'Excluding VAT'}
            </p>
          </div>
        </div>

        {property.construction_info && (
          <>
            <p className="text-sm text-gray-600 mb-2">
              {property.construction_info.year && `Built: ${property.construction_info.year}`}
              {property.construction_info.type && ` • ${property.construction_info.type}`}
              {property.construction_info.has_central_heating && ' • Central Heating'}
            </p>
            
            {/* Construction Status */}
            <div className="mb-2">
              <div className="flex flex-wrap gap-2 mb-2">
                {constructionStatus && (
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    constructionStatus.type === 'completed' ? 'bg-green-100 text-green-800' :
                    constructionStatus.type === 'planned' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {constructionStatus.text}
                  </span>
                )}
                
                {/* Additional construction badges */}
                {property.construction_info.is_renovated && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Renovated
                  </span>
                )}
                {property.construction_info.is_furnished && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    Furnished
                  </span>
                )}
              </div>
              
              {/* Construction Details */}
              {constructionStatus?.details && (
                <div className="bg-gray-50 rounded p-3 text-sm text-gray-700">
                  {constructionStatus.details}
                </div>
              )}
            </div>
          </>
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