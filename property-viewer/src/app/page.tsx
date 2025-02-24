'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Property } from '@/types/property';
import PropertyCard from '@/components/PropertyCard';

export default function Home() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [propertyTypes, setPropertyTypes] = useState<string[]>([]);
  const [filters, setFilters] = useState({
    minPrice: '',
    maxPrice: '',
    minArea: '',
    maxArea: '',
    district: '',
    type: '',
    minYear: '',
    maxYear: '',
  });

  useEffect(() => {
    fetchProperties();
  }, [filters]);

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
          images:images(url, position)
        `)
        .neq('id', 'metadata')
        .order('price_value', { ascending: true });

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

      // District filter with improved text search
      if (filters.district && filters.district.trim()) {
        const district = filters.district.trim();
        console.log('Filtering by district:', district);
        query = query.textSearch('locations.district', district, {
          config: 'bulgarian',
          type: 'websearch'
        });
      }

      console.log('Executing query...');
      const { data, error } = await query;

      if (error) {
        console.error('Query error:', error);
        throw error;
      }
      
      console.log('Got', data?.length, 'results');
      
      // Transform the data
      let transformedData = data.map(property => ({
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
        console.log('After year filtering:', transformedData.length, 'results');
      }

      setProperties(transformedData);
    } catch (error) {
      console.error('Error fetching properties:', error);
      // You might want to set an error state here
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Property Viewer</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {properties.map((property) => (
            <PropertyCard key={property.id} property={property} />
          ))}
        </div>
      )}
    </main>
  );
}
