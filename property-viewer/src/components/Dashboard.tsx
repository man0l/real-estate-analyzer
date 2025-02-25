import { Property } from '@/types/property';

interface DashboardProps {
  properties: Property[];
  filters: {
    district: string;
    minYear: string;
    maxYear: string;
    isRenovated: boolean | null;
    isFurnished: boolean | null;
    minArea: string;
    maxArea: string;
    isPrivateSeller: boolean | null;
    propertyType: string[];
  };
}

export default function Dashboard({ properties, filters }: DashboardProps) {
  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Filter properties based on the current filters
  const filteredProperties = properties.filter(property => {
    if (filters.district && property.location?.district !== filters.district) {
      return false;
    }

    if (filters.propertyType.length > 0 && !filters.propertyType.includes(property.type || '')) {
      return false;
    }

    if (filters.minYear && property.construction_info?.year) {
      const minYear = parseInt(filters.minYear);
      const propertyYear = parseInt(property.construction_info.year.toString());
      if (propertyYear < minYear) {
        return false;
      }
    }

    if (filters.maxYear && property.construction_info?.year) {
      const maxYear = parseInt(filters.maxYear);
      const propertyYear = parseInt(property.construction_info.year.toString());
      if (propertyYear > maxYear) {
        return false;
      }
    }

    if (filters.isRenovated !== null && 
        property.construction_info?.is_renovated !== filters.isRenovated) {
      return false;
    }

    if (filters.isFurnished !== null && 
        property.construction_info?.is_furnished !== filters.isFurnished) {
      return false;
    }

    if (filters.minArea && property.area_m2) {
      const minArea = parseFloat(filters.minArea);
      if (property.area_m2 < minArea) {
        return false;
      }
    }

    if (filters.maxArea && property.area_m2) {
      const maxArea = parseFloat(filters.maxArea);
      if (property.area_m2 > maxArea) {
        return false;
      }
    }

    if (filters.isPrivateSeller !== null && 
        property.is_private_seller !== filters.isPrivateSeller) {
      return false;
    }

    return true;
  });

  // Calculate statistics
  const validProperties = filteredProperties.filter(p => {
    // Convert price to number if it's a string
    const price = typeof p.price_value === 'string' ? parseFloat(p.price_value) : p.price_value;
    
    // Check if district looks like a year (e.g., "2024 г.")
    const districtLooksLikeYear = p.location?.district?.match(/^20\d{2}/);
    
    const hasValidPrice = price && price > 0 && !isNaN(price) && !districtLooksLikeYear;
    
    if (!hasValidPrice) {
      console.log('Property excluded due to invalid price or year-like district:', {
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
  console.log('Valid properties sorted by price:', 
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
  const renovatedProperties = validProperties.filter(p => {
    const isRenovated = p.construction_info?.is_renovated === true;
    if (isRenovated) {
      console.log('Found renovated property:', {
        id: p.id,
        price: p.price_value,
        priceType: typeof p.price_value,
        district: p.location?.district,
        hasAct16: p.construction_info?.has_act16
      });
    }
    return isRenovated;
  });

  // Debug: Log counts and sums
  console.log('Property counts and sums:', {
    total: filteredProperties.length,
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

  const averagePrice = validProperties.length > 0
    ? validProperties.reduce((sum, p) => sum + p.price_value, 0) / validProperties.length
    : 0;

  const averagePricePerSqm = validPropertiesWithArea.length > 0
    ? validPropertiesWithArea.reduce((sum, p) => sum + (p.price_value / (p.area_m2 || 1)), 0) / validPropertiesWithArea.length
    : 0;

  const averagePriceWithAct16 = propertiesWithAct16.length > 0
    ? propertiesWithAct16.reduce((sum, p) => sum + p.price_value, 0) / propertiesWithAct16.length
    : 0;

  const averagePriceWithoutAct16 = propertiesWithoutAct16.length > 0
    ? propertiesWithoutAct16.reduce((sum, p) => sum + p.price_value, 0) / propertiesWithoutAct16.length
    : 0;

  const averagePriceRenovated = renovatedProperties.length > 0
    ? renovatedProperties.reduce((sum, p) => {
        console.log('Adding renovated property price:', { id: p.id, price: p.price_value });
        return sum + p.price_value;
      }, 0) / renovatedProperties.length
    : 0;

  // Debug: Log all averages with their calculations
  console.log('Price averages calculations:', {
    overall: {
      sum: validProperties.reduce((sum, p) => sum + p.price_value, 0),
      count: validProperties.length,
      average: averagePrice
    },
    renovated: {
      sum: renovatedProperties.reduce((sum, p) => sum + p.price_value, 0),
      count: renovatedProperties.length,
      average: averagePriceRenovated,
      prices: renovatedProperties.map(p => ({
        id: p.id,
        price: p.price_value
      }))
    }
  });

  // Calculate statistics by property type
  const propertyTypeStats = validProperties.reduce((acc, p) => {
    if (!p.type) return acc;
    if (!acc[p.type]) {
      acc[p.type] = {
        count: 0,
        sum: 0,
        min: Infinity,
        max: -Infinity
      };
    }
    acc[p.type].count++;
    acc[p.type].sum += p.price_value;
    acc[p.type].min = Math.min(acc[p.type].min, p.price_value);
    acc[p.type].max = Math.max(acc[p.type].max, p.price_value);
    return acc;
  }, {} as Record<string, { count: number; sum: number; min: number; max: number; }>);

  // Calculate averages and sort by count
  const propertyTypeStatsArray = Object.entries(propertyTypeStats)
    .map(([type, stats]) => ({
      type,
      count: stats.count,
      average: stats.sum / stats.count,
      min: stats.min,
      max: stats.max
    }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Market Statistics</h2>
        
        <div className="grid grid-cols-1 gap-6">
          {/* Overall Market Statistics */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-lg mb-3">Overall Market Statistics</h3>
            
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-500">Average Price ({filters.propertyType.length > 0 ? filters.propertyType.join(', ') : 'All Properties'})</p>
                <p className="text-xl font-semibold">{formatCurrency(averagePrice)}</p>
                <p className="text-xs text-gray-400">Based on {validProperties.length} properties with valid prices</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Average Price per m² ({filters.propertyType.length > 0 ? filters.propertyType.join(', ') : 'All Properties'})</p>
                <p className="text-xl font-semibold">{formatCurrency(averagePricePerSqm)} / m²</p>
                <p className="text-xs text-gray-400">Based on {validPropertiesWithArea.length} properties with valid area</p>
              </div>

              <div>
                <p className="text-sm text-gray-500">Total Properties</p>
                <p className="text-xl font-semibold">{validProperties.length}</p>
                <p className="text-xs text-gray-400">With valid prices</p>
              </div>
            </div>
          </div>
          
          {/* Statistics by Property Type */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-lg mb-3">Statistics by Property Type</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {propertyTypeStatsArray.map(stats => (
                <div key={stats.type} className="p-3 bg-white rounded shadow-sm">
                  <h4 className="font-medium text-gray-900">{stats.type}</h4>
                  <div className="mt-2 space-y-1">
                    <p className="text-sm text-gray-500">
                      Average: <span className="font-medium">{formatCurrency(stats.average)}</span>
                    </p>
                    <p className="text-sm text-gray-500">
                      Range: <span className="font-medium">{formatCurrency(stats.min)} - {formatCurrency(stats.max)}</span>
                    </p>
                    <p className="text-sm text-gray-500">
                      Count: <span className="font-medium">{stats.count}</span>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Filtered Statistics */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-lg mb-3">Filtered Statistics</h3>
            
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-500">Average Price with Act 16</p>
                <p className="text-xl font-semibold">{formatCurrency(averagePriceWithAct16)}</p>
                <p className="text-xs text-gray-400">Based on {propertiesWithAct16.length} properties</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Average Price without Act 16</p>
                <p className="text-xl font-semibold">{formatCurrency(averagePriceWithoutAct16)}</p>
                <p className="text-xs text-gray-400">Based on {propertiesWithoutAct16.length} properties</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Average Price for Renovated Properties</p>
                <p className="text-xl font-semibold">{formatCurrency(averagePriceRenovated)}</p>
                <p className="text-xs text-gray-400">Based on {renovatedProperties.length} properties</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Filtered Results</h2>
        <div className="text-lg mb-4">
          Found {validProperties.length} properties with valid prices matching your criteria
        </div>
      </div>
    </div>
  );
} 