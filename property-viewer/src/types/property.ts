export interface Property {
  id: string;
  type: string;
  url: string;
  price_value: number;
  price_currency: string;
  includes_vat: boolean;
  area_m2: number | null;
  views: number | null;
  last_modified: string | null;
  image_count: number | null;
  description: string | null;
  is_private_seller: boolean | null;
  created_at: string;
  location?: {
    city: string | null;
    district: string | null;
  };
  floor_info?: {
    current_floor: number | null;
    total_floors: number | null;
  };
  construction_info?: {
    type: string | null;
    year: number | null;
    has_central_heating: boolean | null;
    is_renovated: boolean | null;
    is_furnished: boolean | null;
    has_act16: boolean | null;
    is_interior: boolean | null;
    confidence: 'high' | 'medium' | 'low' | null;
    act16_plan_date: string | null;
    act16_details: string | null;
  };
  contact_info?: {
    broker_name: string | null;
    phone: string | null;
  };
  monthly_payment?: {
    value: number | null;
    currency: string | null;
  };
  features: string[];
  images: {
    url: string;
    storage_url: string | null;
    position: number | null;
  }[];
}

export interface CrawlVersion {
  id: number;
  created_at: string;
  total_properties: number | null;
  is_complete: boolean;
} 