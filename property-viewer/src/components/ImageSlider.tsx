import { useState } from 'react';
import Slider from 'react-slick';
import { Dialog } from '@headlessui/react';
import 'slick-carousel/slick/slick.css';
import 'slick-carousel/slick/slick-theme.css';

interface ImageSliderProps {
  images: string[];
}

export default function ImageSlider({ images }: ImageSliderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  if (!images || images.length === 0) {
    return (
      <div className="h-64 bg-gray-200 flex items-center justify-center">
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
  };

  return (
    <>
      <div className="relative h-64 overflow-hidden rounded-lg">
        <Slider {...settings}>
          {images.map((image, index) => (
            <div key={index} className="h-64">
              <img
                src={image}
                alt={`Property image ${index + 1}`}
                className="w-full h-full object-cover cursor-pointer"
                onClick={() => {
                  setCurrentImageIndex(index);
                  setIsOpen(true);
                }}
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
        <div className="fixed inset-0 bg-black/70" aria-hidden="true" />

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-4xl bg-white rounded-lg">
            <div className="relative">
              <button
                onClick={() => setIsOpen(false)}
                className="absolute right-4 top-4 z-10 text-white bg-black/50 rounded-full p-2"
              >
                ✕
              </button>
              <Slider {...settings} initialSlide={currentImageIndex}>
                {images.map((image, index) => (
                  <div key={index} className="h-[80vh]">
                    <img
                      src={image}
                      alt={`Property image ${index + 1}`}
                      className="w-full h-full object-contain"
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