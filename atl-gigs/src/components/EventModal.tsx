import { Fragment } from "react";
import { Dialog, Transition } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { format } from "date-fns";
import { Event } from "../types";

interface EventModalProps {
  event: Event;
  onClose: () => void;
}

export default function EventModal({ event, onClose }: EventModalProps) {
  const {
    venue,
    date,
    doors_time,
    show_time,
    artists,
    adv_price,
    dos_price,
    price,
    ticket_url,
    info_url,
    image_url,
  } = event;

  const formattedDate = format(new Date(date), "EEEE, MMMM d, yyyy");

  return (
    <Transition.Root show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-90 dark:bg-zinc-900 dark:bg-opacity-95 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-gray-50 dark:bg-zinc-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
                <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
                  <button
                    type="button"
                    className="rounded-md bg-gray-50 dark:bg-zinc-800 text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  {image_url && (
                    <div className="w-full sm:w-1/3 mb-4 sm:mb-0 sm:mr-4">
                      <img
                        src={image_url}
                        alt={artists[0]?.name || "Event image"}
                        className="w-full h-auto rounded-lg"
                      />
                    </div>
                  )}

                  <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <Dialog.Title
                      as="h3"
                      className="text-2xl font-semibold leading-6 text-gray-900 dark:text-zinc-100"
                    >
                      {artists[0]?.name}
                    </Dialog.Title>

                    {artists.length > 1 && (
                      <div className="mt-2">
                        <p className="text-sm text-gray-500 dark:text-zinc-300">
                          with{" "}
                          {artists
                            .slice(1)
                            .map((a) => a.name)
                            .join(", ")}
                        </p>
                      </div>
                    )}

                    <div className="mt-4">
                      <p className="text-sm text-gray-500 dark:text-zinc-300">
                        {formattedDate}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-zinc-300">
                        {venue}
                      </p>
                      {doors_time && show_time && (
                        <p className="text-sm text-gray-500 dark:text-zinc-300">
                          Doors: {doors_time} | Show: {show_time}
                        </p>
                      )}
                    </div>

                    <div className="mt-4">
                      {price && (
                        <p className="text-sm font-medium text-gray-900 dark:text-zinc-100">
                          Price: {price}
                        </p>
                      )}
                      {adv_price && dos_price && (
                        <p className="text-sm font-medium text-gray-900 dark:text-zinc-100">
                          Advance: {adv_price} | Door: {dos_price}
                        </p>
                      )}
                    </div>

                    <div className="mt-6 flex gap-4">
                      <a
                        href={ticket_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex w-fit px-4 py-1.5 bg-purple-700 text-white rounded-md hover:bg-purple-800 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500 text-base font-semibold"
                      >
                        Buy Tickets
                      </a>
                      {info_url && (
                        <a
                          href={info_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex w-fit px-4 py-1.5 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 rounded-md border border-gray-300 dark:border-zinc-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors duration-200"
                        >
                          More Info
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
