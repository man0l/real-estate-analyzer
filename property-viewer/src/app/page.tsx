'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Property } from '@/types/property';
import PropertyThumbnail from '@/components/PropertyThumbnail';
import PropertyModal from '@/components/PropertyModal';

export default function Home() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [propertyTypes, setPropertyTypes] = useState<string[]>([]);
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

  // Add stats state
  const [stats, setStats] = useState({
    totalProperties: 0,
    privateSellers: 0,
    brokerListings: 0,
  });

  useEffect(() => {
    fetchProperties();
  }, [filters]);

  useEffect(() => {
    // Calculate stats from properties
    if (properties.length > 0) {
      setStats({
        totalProperties: properties.length,
        privateSellers: properties.filter(p => p.is_private_seller).length,
        brokerListings: properties.filter(p => !p.is_private_seller).length,
      });
    }
  }, [properties]);

  useEffect(() => {
    // Extract unique property types from the data
    if (properties.length > 0) {
      const types = [...new Set(properties.map(p => p.type))];
      setPropertyTypes(types.sort());
    }
  }, [properties]);

  async function fetchProperties() {
    setLoading(true);
    try {
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
        .neq('id', 'metadata')
        .order('price_value', { ascending: true });

      // Apply property IDs filter if provided
      if (filters.propertyIds.trim()) {
        const ids = filters.propertyIds.split(',').map(id => id.trim()).filter(id => id);
        if (ids.length > 0) {
          query = query.in('id', ids);
        }
      }

      // Apply numeric filters with null checks
      if (filters.minPrice) {
        const minPrice = parseInt(filters.minPrice);
        console.log('Filtering by min price:', minPrice);
        query = query.gte('price_value', minPrice);
      }
      if (filters.maxPrice) {
        const maxPrice = parseInt(filters.maxPrice);
        console.log('Filtering by max price:', maxPrice);
        query = query.lte('price_value', maxPrice);
      }
      if (filters.minArea) {
        const minArea = parseInt(filters.minArea);
        console.log('Filtering by min area:', minArea);
        query = query.gte('area_m2', minArea);
      }
      if (filters.maxArea) {
        const maxArea = parseInt(filters.maxArea);
        console.log('Filtering by max area:', maxArea);
        query = query.lte('area_m2', maxArea);
      }

      // Property type filter
      if (filters.type) {
        console.log('Filtering by type:', filters.type);
        query = query.eq('type', filters.type);
      }

      // Private seller filter
      if (filters.isPrivateSeller !== null) {
        console.log('Filtering by private seller:', filters.isPrivateSeller);
        query = query.eq('is_private_seller', filters.isPrivateSeller);
      }

      // District filter with improved text search
      if (filters.district && filters.district.trim()) {
        const district = filters.district.trim();
        console.log('Filtering by district:', district);
        query = query.textSearch('locations.district', district, {
          config: 'bulgarian',
          type: 'websearch'
        });
      }

      console.log('Executing initial query...');
      const { data: initialData, error: initialError } = await query;

      if (initialError) {
        console.error('Initial query error:', initialError);
        throw initialError;
      }

      if (!initialData) {
        console.log('No data returned from query');
        setProperties([]);
        return;
      }

      // Transform the data
      let transformedData = initialData.map(property => ({
        ...property,
        features: property.features?.map((f: { feature: string }) => f.feature) || [],
        images: property.images?.sort((a: { position: number | null }, b: { position: number | null }) => 
          (a.position || 0) - (b.position || 0)
        ) || []
      }));

      // Apply construction year filtering if needed
      if (filters.minYear || filters.maxYear) {
        console.log('Filtering by construction year...');
        transformedData = transformedData.filter(property => {
          const year = property.construction_info?.year;
          if (!year) return false;
          
          if (filters.minYear && year < parseInt(filters.minYear)) return false;
          if (filters.maxYear && year > parseInt(filters.maxYear)) return false;
          
          return true;
        });
      }

      // Apply renovation status filter
      if (filters.isRenovated !== null) {
        console.log('Filtering by renovation status:', filters.isRenovated);
        transformedData = transformedData.filter(property => 
          property.construction_info?.is_renovated === filters.isRenovated
        );
      }

      // Apply furnishing status filter
      if (filters.isFurnished !== null) {
        console.log('Filtering by furnishing status:', filters.isFurnished);
        transformedData = transformedData.filter(property => 
          property.construction_info?.is_furnished === filters.isFurnished
        );
      }

      // Apply Act 16 status filter
      if (filters.hasAct16 !== null) {
        console.log('Filtering by Act 16 status:', filters.hasAct16);
        transformedData = transformedData.filter(property => 
          property.construction_info?.has_act16 === filters.hasAct16
        );
      }

      // Apply Act 16 planned date filter
      if (filters.minAct16Date) {
        const minDate = new Date(filters.minAct16Date);
        console.log('Filtering by min Act 16 date:', minDate);
        transformedData = transformedData.filter(property => {
          const planDate = property.construction_info?.act16_plan_date;
          if (!planDate) return false;
          return new Date(planDate) >= minDate;
        });
      }
      if (filters.maxAct16Date) {
        const maxDate = new Date(filters.maxAct16Date);
        console.log('Filtering by max Act 16 date:', maxDate);
        transformedData = transformedData.filter(property => {
          const planDate = property.construction_info?.act16_plan_date;
          if (!planDate) return false;
          return new Date(planDate) <= maxDate;
        });
      }

      console.log('Final results:', transformedData.length);
      setProperties(transformedData);
    } catch (error) {
      console.error('Error fetching properties:', error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8">Property Viewer</h1>

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
          <input
            type="text"
            placeholder="Search district..."
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={filters.district}
            onChange={(e) => setFilters({ ...filters, district: e.target.value })}
          />
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
  );
}
