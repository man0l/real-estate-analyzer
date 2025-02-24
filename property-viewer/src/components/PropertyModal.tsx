import { Property } from '@/types/property';
import { Dialog } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import ImageSlider from './ImageSlider';

interface PropertyModalProps {
  property: Property;
  isOpen: boolean;
  onClose: () => void;
}

export default function PropertyModal({ property, isOpen, onClose }: PropertyModalProps) {
  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      className="relative z-50"
    >
      <div className="fixed inset-0 bg-black/70" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="mx-auto w-full max-h-[90vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
          {/* Header with close button */}
          <div className="relative z-10 bg-white p-4 flex justify-between items-center border-b">
            <div>
              <h2 className="text-xl font-bold text-gray-900">{property.type}</h2>
              <p className="text-gray-600">{property.location?.district}</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xl font-bold text-gray-900">
                  {property.price_value.toLocaleString()} {property.price_currency}
                </p>
                <p className="text-sm text-gray-500">
                  {property.includes_vat ? 'Including VAT' : 'Excluding VAT'}
                </p>
              </div>
              <button
                onClick={onClose}
                className="rounded-full bg-gray-100 p-2 hover:bg-gray-200 transition-colors"
              >
                <XMarkIcon className="h-6 w-6 text-gray-600" />
              </button>
            </div>
          </div>

          {/* Main content area with image slider and details */}
          <div className="flex-1 overflow-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">
              {/* Left side - Image slider */}
              <div className="relative h-[60vh] lg:h-[80vh] bg-gray-100">
                <ImageSlider images={property.images.map(img => img.url)} />
              </div>

              {/* Right side - Property details */}
              <div className="p-6 overflow-y-auto max-h-[60vh] lg:max-h-[80vh]">
                {/* Quick stats */}
                <div className="flex gap-4 mb-6 flex-wrap">
                  <div className="px-4 py-2 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Area</p>
                    <p className="font-semibold">{property.area_m2} m²</p>
                  </div>
                  {property.floor_info && (
                    <div className="px-4 py-2 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Floor</p>
                      <p className="font-semibold">
                        {property.floor_info.current_floor}/{property.floor_info.total_floors}
                      </p>
                    </div>
                  )}
                  {property.construction_info && (
                    <div className="px-4 py-2 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Year</p>
                      <p className="font-semibold">{property.construction_info.year}</p>
                    </div>
                  )}
                </div>

                {/* Construction details */}
                {property.construction_info && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Construction</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-gray-600">Type</p>
                          <p className="font-medium">{property.construction_info.type}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Central Heating</p>
                          <p className="font-medium">
                            {property.construction_info.has_central_heating ? 'Yes' : 'No'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Monthly payment */}
                {property.monthly_payment && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Monthly Payment</h3>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <p className="text-lg font-bold text-blue-600">
                        {property.monthly_payment.value} {property.monthly_payment.currency}/month
                      </p>
                    </div>
                  </div>
                )}

                {/* Features */}
                {property.features.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Features</h3>
                    <div className="flex flex-wrap gap-2">
                      {property.features.map((feature, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Description */}
                {property.description && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Description</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-gray-600 whitespace-pre-line">{property.description}</p>
                    </div>
                  </div>
                )}

                {/* Contact info */}
                {property.contact_info && (
                  <div className="mt-auto pt-4 border-t">
                    <h3 className="font-semibold text-gray-900 mb-2">Contact</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="font-medium">{property.contact_info.broker_name}</p>
                      <p className="text-gray-600">{property.contact_info.phone}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
} 