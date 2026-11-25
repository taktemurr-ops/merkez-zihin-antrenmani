import 'package:flutter/material.dart';
import 'package:studio_core/app/approved_hub.dart';

/// Onaylı tasarım (Oyun Merkezleri · Tasarım Örnekleri).
const approvedStyle = ApprovedHubStyle(
  background: [Color(0xFF1A3C8C), Color(0xFF14205E), Color(0xFF0A0E36)],
  accent: Color(0xFF2FE0F5),
  card: Color(0xFF1C3A8A),
  play: Color(0xFF22C3E6),
  number: Color(0xFF3FE0FF),
  heroAsset: 'assets/approved/hero.png',
  heroTitle: true,
  blocks: [ApprovedBlock.dailyChallenge, ApprovedBlock.brainStats, ApprovedBlock.featured],
  featuredKey: 'featured',
  featured: ['oyun-hafiza-dizisi', 'oyun-schulte-tablosu', 'oyun-oruntu-tamamlama', 'oyun-tepki-ve-odak'],
  tileArt: {
    'oyun-hafiza-dizisi': 'assets/approved/tile_hafiza.png',
    'oyun-schulte-tablosu': 'assets/approved/tile_dikkat.png',
    'oyun-oruntu-tamamlama': 'assets/approved/tile_mantik.png',
    'oyun-tepki-ve-odak': 'assets/approved/tile_refleks.png',
  },
  tilesPerPage: 4,
  challengeGameId: 'oyun-gunluk-beyin-egzersizi-programi',
);
