import { useState } from 'react';
import Image from 'next/image';
import Slider from 'react-slick';
import { Dialog } from '@headlessui/react';
import 'slick-carousel/slick/slick.css';
import 'slick-carousel/slick/slick-theme.css';

interface ImageSliderProps {
  images: {
    url: string;
    storage_url: string | null;
  }[];
}

export default function ImageSlider({ images }: ImageSliderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  if (!images || images.length === 0) {
    return (
      <div className="h-full bg-gray-200 flex items-center justify-center">
        <p className="text-gray-500">No images available</p>
      </div>
    );
  }

  const settings = {
    dots: true,
    infinite: true,
    speed: 500,
    slidesToShow: 1,
    slidesToScroll: 1,
    beforeChange: (_: any, next: number) => setCurrentImageIndex(next),
    adaptiveHeight: true,
  };

  return (
    <>
      <div className="relative h-full">
        <Slider {...settings}>
          {images.map((image, index) => (
            <div key={index} className="relative h-full aspect-[4/3]">
              <Image
                src={image.storage_url || image.url}
                alt={`Property image ${index + 1}`}
                fill
                sizes="(max-width: 1024px) 100vw, 50vw"
                className="object-contain cursor-pointer"
                onClick={() => {
                  setCurrentImageIndex(index);
                  setIsOpen(true);
                }}
                priority={index === 0}
              />
            </div>
          ))}
        </Slider>
      </div>

      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/90" aria-hidden="true" />

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-5xl">
            <div className="relative">
              <button
                onClick={() => setIsOpen(false)}
                className="absolute right-4 top-4 z-10 text-white bg-black/50 rounded-full p-2 hover:bg-black/70"
              >
                ✕
              </button>
              <Slider {...settings} initialSlide={currentImageIndex}>
                {images.map((image, index) => (
                  <div key={index} className="relative h-[80vh]">
                    <Image
                      src={image.storage_url || image.url}
                      alt={`Property image ${index + 1}`}
                      fill
                      sizes="100vw"
                      className="object-contain"
                      priority={index === currentImageIndex}
                    />
                  </div>
                ))}
              </Slider>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </>
  );
} 