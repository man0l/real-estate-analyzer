# Property Viewer

A Next.js-based property listing application that displays real estate properties with detailed information about construction status, features, and more.

## Prerequisites

- Node.js 18.x or later
- PostgreSQL with Supabase extensions
- npm or yarn package manager

## Getting Started

1. Clone the repository:
```bash
git clone <repository-url>
cd property-viewer
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Set up environment variables:
Create a `.env.local` file in the root directory with the following variables:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

4. Run the development server:
```bash
npm run dev
# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Features

- Property listing with detailed information
- Advanced filtering options
- Construction status tracking (Act 14, 15, 16)
- Image gallery for each property
- Responsive design for all devices

## Project Structure

```
property-viewer/
├── src/
│   ├── app/              # Next.js app router
│   ├── components/       # React components
│   ├── lib/             # Utility functions and configurations
│   └── types/           # TypeScript type definitions
├── public/              # Static assets
└── README.md           # Project documentation
```

## Database Schema

The application uses Supabase (PostgreSQL) with the following main tables:
- properties
- construction_info
- location
- floor_info
- contact_info
- features
- images

## Learn More

To learn more about the technologies used in this project:

- [Next.js Documentation](https://nextjs.org/docs)
- [Supabase Documentation](https://supabase.io/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs)

## Development

When working on the project, you can:

- Edit components in `src/components/`
- Modify pages in `src/app/`
- Update styles using Tailwind CSS classes
- Add new features by creating new components and routes

## Deployment

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme).

Check out the [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
