'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { Property } from '@/types/property';
import PropertyThumbnail from '@/components/PropertyThumbnail';
import PropertyModal from '@/components/PropertyModal';
import Link from 'next/link';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [propertyTypes, setPropertyTypes] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [filters, setFilters] = useState({
    minPrice: '',
    maxPrice: '',
    minArea: '',
    maxArea: '',
    district: '',
    type: '',
    minYear: '',
    maxYear: '',
    isPrivateSeller: null as boolean | null,
    isRenovated: null as boolean | null,
    isFurnished: null as boolean | null,
    hasAct16: null as boolean | null,
    minAct16Date: '',
    maxAct16Date: '',
    propertyIds: ''
  });

  const [marketStats, setMarketStats] = useState({
    totalProperties: 0,
    avgPrice: 0,
    avgPricePerM2: 0,
    avgPriceWithAct16: 0,
    avgPriceWithoutAct16: 0,
    avgPriceRenovated: 0
  });

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      console.log('Starting property fetch with filters:', filters);
      
      // Main query with all joins
      let query = supabase
        .from('properties')
        .select(`
          *,
          location:locations(*),
          floor_info:floor_info(*),
          construction_info:construction_info(*),
          contact_info:contact_info(*),
          monthly_payment:monthly_payments(*),
          features:features(feature),
          images:images(url, storage_url, position)
        `)
        .neq('id', 'metadata');

      // Apply property IDs filter if provided
      if (filters.propertyIds.trim()) {
        const ids = filters.propertyIds.split(',').map(id => id.trim()).filter(id => id);
        if (ids.length > 0) {
          query = query.in('id', ids);
        }
      }

      // Apply numeric filters with null checks - only if values are provided
      if (filters.minPrice && !isNaN(parseInt(filters.minPrice))) {
        query = query.gte('price_value', parseInt(filters.minPrice));
      }
      if (filters.maxPrice && !isNaN(parseInt(filters.maxPrice))) {
        query = query.lte('price_value', parseInt(filters.maxPrice));
      }
      if (filters.minArea && !isNaN(parseInt(filters.minArea))) {
        query = query.gte('area_m2', parseInt(filters.minArea));
      }
      if (filters.maxArea && !isNaN(parseInt(filters.maxArea))) {
        query = query.lte('area_m2', parseInt(filters.maxArea));
      }

      // Property type filter
      if (filters.type) {
        query = query.eq('type', filters.type);
      }

      // Private seller filter
      if (filters.isPrivateSeller !== null) {
        query = query.eq('is_private_seller', filters.isPrivateSeller);
      }

      // District filter with improved text search
      if (filters.district && filters.district.trim()) {
        query = query.textSearch('locations.district', filters.district.trim(), {
          config: 'bulgarian',
          type: 'websearch'
        });
      }

      console.log('Executing query...');
      const { data: initialData, error: initialError } = await query;

      if (initialError) {
        console.error('Query error:', initialError);
        throw initialError;
      }

      if (!initialData) {
        console.log('No data returned from query');
        setProperties([]);
        return;
      }

      console.log('Initial data count:', initialData.length);

      // Transform the data - handle potential nulls and extract info from features
      let transformedData = initialData.map(property => {
        // Extract price from features if not available in main fields
        let price = property.price_value;
        let area = property.area_m2;
        let district = property.location?.district;

        // Try to extract price and area from features if they're null
        if (property.features) {
          for (const feature of property.features) {
            const featureText = feature.feature;
            
            // Extract price
            if (!price) {
              const priceMatch = featureText.match(/(\d+[\d\s]*)\s*EUR/);
              if (priceMatch) {
                price = parseInt(priceMatch[1].replace(/\s/g, ''));
              }
            }

            // Extract area
            if (!area) {
              const areaMatch = featureText.match(/Площ:\s*(\d+(?:\.\d+)?)\s*(?:m2|кв\.м)/i);
              if (areaMatch) {
                area = parseFloat(areaMatch[1]);
              }
            }

            // Extract district if not available
            if (!district) {
              const districtMatch = featureText.match(/^([^,\n]+)(?:,|\n|$)/);
              if (districtMatch && featureText.length < 50) { // Avoid matching long text
                district = districtMatch[1].trim();
              }
            }
          }
        }

        return {
          ...property,
          price_value: price,
          area_m2: area,
          location: property.location || (district ? { district } : null),
          features: property.features?.map((f: { feature: string }) => f.feature) || [],
          images: (property.images || []).sort((a: { position: number | null }, b: { position: number | null }) => 
            ((a?.position || 0) - (b?.position || 0))
          )
        };
      });

      // Apply construction year filtering if needed - handle potential nulls
      if (filters.minYear || filters.maxYear) {
        transformedData = transformedData.filter(property => {
          const year = property.construction_info?.year;
          if (!year && (filters.minYear || filters.maxYear)) return true; // Keep properties with no year if filtering by year
          
          if (filters.minYear && year && year < parseInt(filters.minYear)) return false;
          if (filters.maxYear && year && year > parseInt(filters.maxYear)) return false;
          
          return true;
        });
      }

      // Apply renovation status filter - handle potential nulls
      if (filters.isRenovated !== null) {
        transformedData = transformedData.filter(property => 
          property.construction_info?.is_renovated === undefined || 
          property.construction_info?.is_renovated === filters.isRenovated
        );
      }

      // Apply furnishing status filter - handle potential nulls
      if (filters.isFurnished !== null) {
        transformedData = transformedData.filter(property => 
          property.construction_info?.is_furnished === undefined || 
          property.construction_info?.is_furnished === filters.isFurnished
        );
      }

      // Apply Act 16 status filter - handle potential nulls
      if (filters.hasAct16 !== null) {
        transformedData = transformedData.filter(property => 
          property.construction_info?.has_act16 === undefined || 
          property.construction_info?.has_act16 === filters.hasAct16
        );
      }

      // Apply Act 16 planned date filter - handle potential nulls
      if (filters.minAct16Date) {
        const minDate = new Date(filters.minAct16Date);
        transformedData = transformedData.filter(property => {
          const planDate = property.construction_info?.act16_plan_date;
          if (!planDate) return true; // Keep properties with no date
          return new Date(planDate) >= minDate;
        });
      }
      if (filters.maxAct16Date) {
        const maxDate = new Date(filters.maxAct16Date);
        transformedData = transformedData.filter(property => {
          const planDate = property.construction_info?.act16_plan_date;
          if (!planDate) return true; // Keep properties with no date
          return new Date(planDate) <= maxDate;
        });
      }

      console.log('Final filtered results:', transformedData.length);
      setProperties(transformedData);
    } catch (error) {
      console.error('Error fetching properties:', error);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const fetchMarketStats = useCallback(async () => {
    try {
      // Calculate stats from current properties
      const validProperties = properties.filter(p => {
        // Convert price to number if it's a string
        const price = typeof p.price_value === 'string' ? parseFloat(p.price_value) : p.price_value;
        
        // Check if district looks like a year (e.g., "2024 г.")
        const districtLooksLikeYear = p.location?.district?.match(/^20\d{2}/);
        
        const hasValidPrice = price && price > 0 && !isNaN(price) && !districtLooksLikeYear;
        
        if (!hasValidPrice) {
          console.log('Property excluded from market stats due to invalid price or year-like district:', {
            id: p.id,
            originalPrice: p.price_value,
            convertedPrice: price,
            district: p.location?.district,
            priceType: typeof p.price_value,
            isPrivateSeller: p.is_private_seller,
            excludedReason: districtLooksLikeYear ? 'district looks like year' : 'invalid price'
          });
        }

        // Store the converted price
        if (hasValidPrice) {
          p.price_value = price;
        }
        return hasValidPrice;
      });

      // Debug: Log properties sorted by price
      console.log('Valid properties for market stats sorted by price:', 
        validProperties
          .sort((a, b) => (b.price_value || 0) - (a.price_value || 0))
          .map(p => ({
            id: p.id,
            price: p.price_value,
            priceType: typeof p.price_value,
            area: p.area_m2,
            district: p.location?.district,
            isPrivateSeller: p.is_private_seller,
            hasAct16: p.construction_info?.has_act16,
            isRenovated: p.construction_info?.is_renovated
          }))
      );

      const validPropertiesWithArea = validProperties.filter(p => p.area_m2 && p.area_m2 > 0 && !isNaN(p.area_m2));
      const propertiesWithAct16 = validProperties.filter(p => p.construction_info?.has_act16 === true);
      const propertiesWithoutAct16 = validProperties.filter(p => p.construction_info?.has_act16 === false);
      const renovatedProperties = validProperties.filter(p => p.construction_info?.is_renovated === true);

      // Debug: Log counts and sums
      console.log('Market Stats - Property counts and sums:', {
        total: properties.length,
        valid: validProperties.length,
        withArea: validPropertiesWithArea.length,
        withAct16: propertiesWithAct16.length,
        withoutAct16: propertiesWithoutAct16.length,
        renovated: {
          count: renovatedProperties.length,
          prices: renovatedProperties.map(p => p.price_value),
          sum: renovatedProperties.reduce((sum, p) => sum + p.price_value, 0)
        }
      });

      const avgPrice = validProperties.length > 0
        ? Math.round(validProperties.reduce((sum, p) => sum + p.price_value, 0) / validProperties.length)
        : 0;

      const avgPricePerM2 = validPropertiesWithArea.length > 0
        ? Math.round(validPropertiesWithArea.reduce((sum, p) => {
            // Since we filtered for valid areas above, we can safely use || 1 here
            const area = p.area_m2 || 1;
            return sum + (p.price_value / area);
          }, 0) / validPropertiesWithArea.length)
        : 0;

      const avgPriceWithAct16 = propertiesWithAct16.length > 0
        ? Math.round(propertiesWithAct16.reduce((sum, p) => sum + p.price_value, 0) / propertiesWithAct16.length)
        : 0;

      const avgPriceWithoutAct16 = propertiesWithoutAct16.length > 0
        ? Math.round(propertiesWithoutAct16.reduce((sum, p) => sum + p.price_value, 0) / propertiesWithoutAct16.length)
        : 0;

      const avgPriceRenovated = renovatedProperties.length > 0
        ? Math.round(renovatedProperties.reduce((sum, p) => sum + p.price_value, 0) / renovatedProperties.length)
        : 0;

      // Debug: Log all averages with their calculations
      console.log('Market Stats - Price averages calculations:', {
        overall: {
          sum: validProperties.reduce((sum, p) => sum + p.price_value, 0),
          count: validProperties.length,
          average: avgPrice
        },
        renovated: {
          sum: renovatedProperties.reduce((sum, p) => sum + p.price_value, 0),
          count: renovatedProperties.length,
          average: avgPriceRenovated,
          prices: renovatedProperties.map(p => ({
            id: p.id,
            price: p.price_value
          }))
        }
      });

      setMarketStats({
        totalProperties: validProperties.length,
        avgPrice,
        avgPricePerM2,
        avgPriceWithAct16,
        avgPriceWithoutAct16,
        avgPriceRenovated
      });
    } catch (error) {
      console.error('Error calculating market stats:', error);
    }
  }, [properties]);

  useEffect(() => {
    fetchFilterOptions();
    fetchMarketStats();
    fetchProperties();
  }, [fetchMarketStats, fetchProperties]);

  // Add effect to refetch when filters change
  useEffect(() => {
    fetchProperties();
  }, [filters, fetchProperties]);

  // Add effect to update market stats when properties change
  useEffect(() => {
    fetchMarketStats();
  }, [properties, fetchMarketStats]);

  // Fetch filter options from database
  async function fetchFilterOptions() {
    try {
      // Fetch property types
      const { data: typeData, error: typeError } = await supabase
        .from('properties')
        .select('type')
        .not('type', 'is', null);

      if (typeError) {
        console.error('Error fetching property types:', typeError);
      } else if (typeData) {
        const types = [...new Set(typeData.map(p => p.type))].filter(Boolean).sort();
        setPropertyTypes(types);
      }

      // Fetch districts
      const { data: districtData, error: districtError } = await supabase
        .from('locations')
        .select('district')
        .not('district', 'is', null);

      if (districtError) {
        console.error('Error fetching districts:', districtError);
      } else if (districtData) {
        const uniqueDistricts = [...new Set(districtData.map(d => d.district))].filter(Boolean).sort();
        setDistricts(uniqueDistricts);
      }
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Property Listings</h1>
        <button 
          onClick={() => router.push('/dashboard')}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          View Dashboard
        </button>
      </div>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Overall Market Statistics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Average Price (All Properties)</div>
            <div className="text-2xl font-bold">{Math.round(marketStats.avgPrice).toLocaleString()} €</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Average Price per m² (All Properties)</div>
            <div className="text-2xl font-bold">{Math.round(marketStats.avgPricePerM2).toLocaleString()} € / m²</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Total Properties</div>
            <div className="text-2xl font-bold">{marketStats.totalProperties.toLocaleString()}</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Average Price with Act 16</div>
            <div className="text-2xl font-bold">{Math.round(marketStats.avgPriceWithAct16).toLocaleString()} €</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Average Price without Act 16</div>
            <div className="text-2xl font-bold">{Math.round(marketStats.avgPriceWithoutAct16).toLocaleString()} €</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">Average Price for Renovated Properties</div>
            <div className="text-2xl font-bold">{Math.round(marketStats.avgPriceRenovated).toLocaleString()} €</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Property IDs (comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g., 1b123,1c456"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.propertyIds}
              onChange={(e) => setFilters({ ...filters, propertyIds: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Price Range (EUR)
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Min"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.minPrice}
                onChange={(e) => setFilters({ ...filters, minPrice: e.target.value })}
              />
              <input
                type="number"
                placeholder="Max"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.maxPrice}
                onChange={(e) => setFilters({ ...filters, maxPrice: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Area Range (m²)
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Min"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.minArea}
                onChange={(e) => setFilters({ ...filters, minArea: e.target.value })}
              />
              <input
                type="number"
                placeholder="Max"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.maxArea}
                onChange={(e) => setFilters({ ...filters, maxArea: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Construction Year
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="From"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.minYear}
                onChange={(e) => setFilters({ ...filters, minYear: e.target.value })}
              />
              <input
                type="number"
                placeholder="To"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.maxYear}
                onChange={(e) => setFilters({ ...filters, maxYear: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Property Type
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
            >
              <option value="">All Types</option>
              {propertyTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              District
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.district}
              onChange={(e) => setFilters({ ...filters, district: e.target.value })}
            >
              <option value="">All Districts</option>
              {districts.map((district) => (
                <option key={district} value={district}>
                  {district}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Seller Type
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.isPrivateSeller === null ? '' : filters.isPrivateSeller.toString()}
              onChange={(e) => {
                const value = e.target.value;
                setFilters({ 
                  ...filters, 
                  isPrivateSeller: value === '' ? null : value === 'true'
                });
              }}
            >
              <option value="">All Sellers</option>
              <option value="true">Private Sellers</option>
              <option value="false">Brokers</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Renovation Status
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.isRenovated === null ? '' : filters.isRenovated.toString()}
              onChange={(e) => {
                const value = e.target.value;
                setFilters({ 
                  ...filters, 
                  isRenovated: value === '' ? null : value === 'true'
                });
              }}
            >
              <option value="">All Properties</option>
              <option value="true">Renovated</option>
              <option value="false">Needs Renovation</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Furnishing Status
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.isFurnished === null ? '' : filters.isFurnished.toString()}
              onChange={(e) => {
                const value = e.target.value;
                setFilters({ 
                  ...filters, 
                  isFurnished: value === '' ? null : value === 'true'
                });
              }}
            >
              <option value="">All Properties</option>
              <option value="true">Furnished</option>
              <option value="false">Unfurnished</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Building Status
            </label>
            <select
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.hasAct16 === null ? '' : filters.hasAct16.toString()}
              onChange={(e) => {
                const value = e.target.value;
                setFilters({ 
                  ...filters, 
                  hasAct16: value === '' ? null : value === 'true'
                });
              }}
            >
              <option value="">All Buildings</option>
              <option value="true">With Act 16</option>
              <option value="false">Under Construction</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Planned Completion
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                placeholder="From"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.minAct16Date}
                onChange={(e) => setFilters({ ...filters, minAct16Date: e.target.value })}
              />
              <input
                type="date"
                placeholder="To"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={filters.maxAct16Date}
                onChange={(e) => setFilters({ ...filters, maxAct16Date: e.target.value })}
              />
            </div>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({
                minPrice: '',
                maxPrice: '',
                minArea: '',
                maxArea: '',
                district: '',
                type: '',
                minYear: '',
                maxYear: '',
                isPrivateSeller: null,
                isRenovated: null,
                isFurnished: null,
                hasAct16: null,
                minAct16Date: '',
                maxAct16Date: '',
                propertyIds: '',
              })}
              className="w-full py-2 px-4 text-sm text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              Clear all filters
            </button>
          </div>
        </div>

        <div className="text-sm text-gray-600 mb-4">
          Found {properties.length} properties
        </div>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading properties...</p>
          </div>
        ) : properties.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No properties found matching your criteria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {properties.map((property) => (
              <PropertyThumbnail
                key={property.id}
                property={property}
                onClick={() => setSelectedProperty(property)}
              />
            ))}
          </div>
        )}

        {selectedProperty && (
          <PropertyModal
            property={selectedProperty}
            isOpen={!!selectedProperty}
            onClose={() => setSelectedProperty(null)}
          />
        )}
      </div>
    </div>
  );
}
