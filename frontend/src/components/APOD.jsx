'use client'

import { useState, useEffect } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { ExternalLink, Calendar, Star } from "lucide-react";

const NASA_API_KEY = process.env.NEXT_PUBLIC_NASA_API_KEY || "DEMO_KEY";

export default function APOD() {
  const [apod, setApod] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAPOD();
  }, []);

  const fetchAPOD = async () => {
    try {
      const response = await fetch(
        `https://api.nasa.gov/planetary/apod?api_key=${NASA_API_KEY}`
      );
      if (!response.ok) {
        if (response.status === 429) {
          throw new Error("NASA API Rate Limit Exceeded (DEMO_KEY)");
        }
        throw new Error(`NASA API Service Error: ${response.status}`);
      }
      const data = await response.json();
      setApod(data);
    } catch (err) {
      setError(err.message || "Failed to fetch APOD");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-astro-primary/10 via-black/50 to-astro-secondary/10 p-8 text-center">
        <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/20 border-t-white" />
        <p className="mt-3 text-sm text-slate-400">Loading Astronomy Picture...</p>
      </div>
    );
  }

  if (error || !apod) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-astro-primary/10 via-black/50 to-astro-secondary/10 p-8 text-center">
        <Star className="h-12 w-12 text-slate-500" />
        <p className="mt-3 text-sm text-slate-400">Picture of the day unavailable</p>
        <button
          onClick={fetchAPOD}
          className="mt-4 rounded-lg bg-astro-primary px-4 py-1.5 text-xs font-medium text-white transition hover:bg-astro-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  const isImage = apod.media_type === "image";
  const isVideo = apod.media_type === "video";

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-astro-primary/20 via-[#0A0A0A] to-astro-secondary/10">
      <div className="relative flex-1 overflow-hidden">
        {isImage && apod.url && (
          <motion.div
            initial={{ scale: 1.1, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="absolute inset-0"
          >
            <Image
              src={apod.url}
              alt={apod.title}
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          </motion.div>
        )}
        {isVideo && apod.url && (
          <iframe
            src={apod.url.replace("youtube.com", "youtube-nocookie.com/embed")}
            className="absolute inset-0 h-full w-full rounded-lg"
            allowFullScreen
            title={apod.title}
          />
        )}
        <div className="absolute bottom-6 left-6 right-6">
          <div className="flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 backdrop-blur-sm border border-white/20">
            <Star className="h-4 w-4 text-yellow-400" />
            <span className="text-xs font-semibold text-white uppercase tracking-wider">
              Astronomy Picture of the Day
            </span>
          </div>
        </div>
      </div>

      {/* Content Panel */}
      <div className="border-t border-white/10 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg leading-tight line-clamp-1 text-white">
              {apod.title}
            </h3>
            <p className="mt-1 text-xs text-slate-400 line-clamp-2 leading-relaxed">
              {apod.explanation}
            </p>
          </div>
          <div className="ml-4 flex shrink-0 flex-col items-end gap-1 text-xs text-slate-400">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(apod.date).toLocaleDateString()}
            </div>
            <div>by {apod.copyright || "NASA/APOD"}</div>
          </div>
        </div>
        <div className="mt-4">
          <a
            href={apod.hdurl || apod.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2 text-xs font-medium text-white backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-all"
          >
            View Full Image
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
