'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { Property } from '@/types/property';
import Dashboard from '@/components/Dashboard';
import DashboardFilters from '@/components/DashboardFilters';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const router = useRouter();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [districts, setDistricts] = useState<string[]>([]);
  const [dashboardFilters, setDashboardFilters] = useState({
    district: '',
    minYear: '',
    maxYear: '',
    isRenovated: null as boolean | null,
    isFurnished: null as boolean | null,
    minArea: '',
    maxArea: '',
    isPrivateSeller: null as boolean | null,
    propertyType: [] as string[],
  });

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      // Main query with all joins
      const query = supabase
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

      console.log('Executing dashboard query...');
      const { data: initialData, error: initialError } = await query;

      if (initialError) {
        console.error('Dashboard query error:', initialError);
        throw initialError;
      }

      if (!initialData) {
        console.log('No data returned from query');
        setProperties([]);
        return;
      }

      // Transform the data
      const transformedData = initialData.map(property => {
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
          images: property.images?.sort((a: { position: number | null }, b: { position: number | null }) => 
            (a.position || 0) - (b.position || 0)
          ) || []
        };
      });

      setProperties(transformedData);
    } catch (error) {
      console.error('Error fetching properties:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load effect
  useEffect(() => {
    const init = async () => {
      await fetchDistricts();
      await fetchProperties();
    };
    init();
  }, [fetchProperties]);

  async function fetchDistricts() {
    try {
      const { data, error } = await supabase
        .from('locations')
        .select('district')
        .not('district', 'is', null)
        .order('district');

      if (error) {
        console.error('Error fetching districts:', error);
        return;
      }

      const uniqueDistricts = [...new Set(data.map(d => d.district))];
      setDistricts(uniqueDistricts);
    } catch (error) {
      console.error('Error fetching districts:', error);
    }
  }

  const handleFilterChange = (newFilters: typeof dashboardFilters) => {
    setDashboardFilters(newFilters);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Property Market Dashboard</h1>
        <button 
          onClick={() => router.push('/')}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Back to Properties
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <>
          <DashboardFilters 
            properties={properties} 
            filters={dashboardFilters} 
            onFilterChange={handleFilterChange} 
            districts={districts}
          />
          
          <Dashboard 
            properties={properties} 
            filters={dashboardFilters}
          />
        </>
      )}
    </div>
  );
} 