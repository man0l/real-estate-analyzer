import { useState, useEffect } from 'react';
import { Property } from '@/types/property';

interface DashboardFiltersProps {
  properties: Property[];
  districts: string[];
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
  onFilterChange: (filters: DashboardFiltersProps['filters']) => void;
}

export default function DashboardFilters({ properties, districts, filters, onFilterChange }: DashboardFiltersProps) {
  const [constructionYears, setConstructionYears] = useState({
    min: 0,
    max: 0
  });

  // Get unique property types
  const propertyTypes = [...new Set(properties
    .map(p => p.type)
    .filter(Boolean)
  )].sort();

  // Handle multiple selection for property types
  const handlePropertyTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedOptions = Array.from(e.target.selectedOptions).map(option => option.value);
    onFilterChange({ ...filters, propertyType: selectedOptions });
  };

  useEffect(() => {
    if (properties.length === 0) return;

    // Find min and max construction years
    let minYear = Infinity;
    let maxYear = 0;
    properties.forEach(property => {
      const year = property.construction_info?.year;
      if (year) {
        minYear = Math.min(minYear, year);
        maxYear = Math.max(maxYear, year);
      }
    });
    
    if (minYear !== Infinity && maxYear !== 0) {
      setConstructionYears({ min: minYear, max: maxYear });
    }
  }, [properties]);

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Dashboard Filters</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* District Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            District
          </label>
          <select
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={filters.district}
            onChange={(e) => onFilterChange({ ...filters, district: e.target.value })}
          >
            <option value="">All Districts</option>
            {districts.map((district) => (
              <option key={district} value={district}>
                {district}
              </option>
            ))}
          </select>
        </div>

        {/* Property Type Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Property Types
          </label>
          <select
            multiple
            size={4}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={filters.propertyType}
            onChange={handlePropertyTypeChange}
          >
            {propertyTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
        </div>
        
        {/* Construction Year Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Construction Year Range
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              placeholder="Min"
              min={constructionYears.min}
              max={constructionYears.max}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.minYear}
              onChange={(e) => onFilterChange({ ...filters, minYear: e.target.value })}
            />
            <span className="self-center">-</span>
            <input
              type="number"
              placeholder="Max"
              min={constructionYears.min}
              max={constructionYears.max}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.maxYear}
              onChange={(e) => onFilterChange({ ...filters, maxYear: e.target.value })}
            />
          </div>
        </div>
        
        {/* Area Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Area Range (m²)
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              placeholder="Min"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.minArea}
              onChange={(e) => onFilterChange({ ...filters, minArea: e.target.value })}
            />
            <span className="self-center">-</span>
            <input
              type="number"
              placeholder="Max"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={filters.maxArea}
              onChange={(e) => onFilterChange({ ...filters, maxArea: e.target.value })}
            />
          </div>
        </div>
        
        {/* Property Features Checkboxes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Property Features
          </label>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                id="renovated"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={filters.isRenovated === true}
                onChange={(e) => onFilterChange({ 
                  ...filters, 
                  isRenovated: e.target.checked ? true : null 
                })}
              />
              <label htmlFor="renovated" className="ml-2 block text-sm text-gray-700">
                Renovated
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                id="furnished"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={filters.isFurnished === true}
                onChange={(e) => onFilterChange({ 
                  ...filters, 
                  isFurnished: e.target.checked ? true : null 
                })}
              />
              <label htmlFor="furnished" className="ml-2 block text-sm text-gray-700">
                Furnished
              </label>
            </div>

            <div className="flex items-center">
              <input
                id="privateSeller"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={filters.isPrivateSeller === true}
                onChange={(e) => onFilterChange({ 
                  ...filters, 
                  isPrivateSeller: e.target.checked ? true : null 
                })}
              />
              <label htmlFor="privateSeller" className="ml-2 block text-sm text-gray-700">
                Private Seller
              </label>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-4 flex justify-end">
        <button
          type="button"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          onClick={() => onFilterChange({
            district: '',
            minYear: '',
            maxYear: '',
            isRenovated: null,
            isFurnished: null,
            minArea: '',
            maxArea: '',
            isPrivateSeller: null,
            propertyType: [],
          })}
        >
          Reset Filters
        </button>
      </div>
    </div>
  );
} 