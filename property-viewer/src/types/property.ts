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
    position: number | null;
  }[];
}

export interface CrawlVersion {
  id: number;
  created_at: string;
  total_properties: number | null;
  is_complete: boolean;
} 