#!/usr/bin/env python3
"""
Category Review Web App

A Flask web application for reviewing video categorizations.
Browse categories, view thumbnails, and quickly mark videos as
correctly/incorrectly categorized by toggling the manual flag.

Usage:
    python category_review_app.py [--port 5000] [--dir ~/reel_archive]
    
Then open http://localhost:5000 in your browser.

Keyboard Shortcuts:
    X        - Exclude selected video
    U        - Undo exclusion
    M        - Move to different category
    ←/→      - Navigate between videos
    Escape   - Close modal
"""

import os
import json
import argparse
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, send_from_directory

app = Flask(__name__)

# Configuration - will be set from command line
REEL_ARCHIVE_DIR = os.path.expanduser("~/reel_archive")

# HTML Template with embedded CSS and JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Category Review - {{ category_name if category_name else 'All Categories' }}</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        
        .header {
            background: #16213e;
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .header h1 {
            font-size: 1.5rem;
        }
        
        .header-stats {
            font-size: 0.9rem;
            color: #888;
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }
        
        .header-stats .auto-count { color: #60a5fa; }
        
        .progress-bar {
            width: 100%;
            height: 4px;
            background: #333;
            border-radius: 2px;
            margin-top: 0.5rem;
            overflow: hidden;
        }
        
        .progress-bar .progress {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #22d3ee);
            transition: width 0.3s;
        }
        
        .keyboard-hints {
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.5rem;
        }
        
        .keyboard-hints kbd {
            background: #333;
            padding: 0.1rem 0.4rem;
            border-radius: 3px;
            margin: 0 0.2rem;
        }
        
        .nav {
            background: #0f0f23;
            padding: 1rem 2rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            border-bottom: 1px solid #333;
            align-items: center;
        }
        
        .nav a {
            color: #888;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .nav a:hover {
            background: #1a1a2e;
            color: #fff;
        }
        
        .nav a.active {
            background: #4f46e5;
            color: #fff;
        }
        
        .nav a .count {
            background: rgba(255,255,255,0.2);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            margin-left: 0.3rem;
            font-size: 0.75rem;
        }
        
        .nav .add-category-btn {
            background: #065f46;
            color: #4ade80;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        
        .nav .add-category-btn:hover {
            background: #047857;
        }
        
        .nav-controls {
            display: flex;
            gap: 0.5rem;
            align-items: center;
            margin-left: auto;
        }
        
        .nav-sort-select {
            padding: 0.4rem 0.8rem;
            border: none;
            border-radius: 6px;
            background: #16213e;
            color: #888;
            font-size: 0.8rem;
            cursor: pointer;
        }
        
        .nav-sort-select:hover {
            color: #fff;
        }
        
        .modal-search {
            margin-bottom: 1rem;
        }
        
        .modal-search input {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            background: #0f0f23;
            color: #fff;
            font-size: 0.9rem;
        }
        
        .modal-search input::placeholder {
            color: #666;
        }
        
        .modal-sort-controls {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .modal-sort-btn {
            flex: 1;
            padding: 0.5rem;
            border: none;
            border-radius: 4px;
            background: #0f0f23;
            color: #888;
            font-size: 0.75rem;
            cursor: pointer;
        }
        
        .modal-sort-btn:hover, .modal-sort-btn.active {
            background: #4f46e5;
            color: #fff;
        }
        
        .category-item.hidden {
            display: none !important;
        }
        
        .container {
            padding: 2rem;
            max-width: 1800px;
            margin: 0 auto;
        }
        
        .toolbar {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .search-box {
            flex: 1;
            min-width: 200px;
            max-width: 400px;
        }
        
        .search-box input {
            width: 100%;
            padding: 0.6rem 1rem;
            border: none;
            border-radius: 6px;
            background: #16213e;
            color: #fff;
            font-size: 0.9rem;
        }
        
        .search-box input::placeholder {
            color: #666;
        }
        
        .sort-select {
            padding: 0.6rem 1rem;
            border: none;
            border-radius: 6px;
            background: #16213e;
            color: #fff;
            font-size: 0.9rem;
            cursor: pointer;
        }
        
        .filter-group {
            display: flex;
            gap: 0.5rem;
        }
        
        .filter-group label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
            padding: 0.5rem 1rem;
            background: #16213e;
            border-radius: 6px;
            font-size: 0.85rem;
        }
        
        .filter-group input[type="checkbox"] {
            width: 1rem;
            height: 1rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .video-card {
            background: #16213e;
            border-radius: 12px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s;
            border: 3px solid transparent;
            position: relative;
        }
        
        .video-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.4);
        }
        
        .video-card.selected {
            border-color: #4f46e5;
            box-shadow: 0 0 20px rgba(79, 70, 229, 0.5);
        }
        
        .video-card.excluded {
            border-color: #f87171;
            opacity: 0.5;
            transform: scale(0.95);
        }
        
        .video-card.excluded::after {
            content: '✗ EXCLUDED';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(248, 113, 113, 0.9);
            color: #000;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: bold;
            z-index: 10;
        }
        
        .video-card.excluded img {
            filter: grayscale(100%);
        }
        
        .video-card.moved {
            border-color: #22d3ee;
        }
        
        .video-card.moved::after {
            content: '↪ MOVED';
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(34, 211, 238, 0.9);
            color: #000;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
            z-index: 10;
        }
        
        .video-card img {
            width: 100%;
            aspect-ratio: 9/16;
            object-fit: cover;
            display: block;
        }
        
        .video-card .info {
            padding: 0.75rem;
        }
        
        .video-card .shortcode {
            font-size: 0.75rem;
            color: #888;
            margin-bottom: 0.25rem;
            font-family: monospace;
        }
        
        .video-card .score {
            font-size: 0.8rem;
            color: #60a5fa;
        }
        
        .video-card .keywords {
            font-size: 0.7rem;
            color: #666;
            margin-top: 0.25rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .actions {
            padding: 0.5rem 0.75rem;
            background: rgba(0,0,0,0.2);
            display: flex;
            gap: 0.5rem;
        }
        
        .actions button {
            flex: 1;
            padding: 0.5rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .actions .btn-exclude {
            background: #dc2626;
            color: #fff;
        }
        
        .actions .btn-exclude:hover {
            background: #b91c1c;
        }
        
        .actions .btn-move {
            background: #0891b2;
            color: #fff;
        }
        
        .actions .btn-move:hover {
            background: #0e7490;
        }
        
        .actions .btn-undo {
            background: #059669;
            color: #fff;
        }
        
        .actions .btn-undo:hover {
            background: #047857;
        }
        
        /* Modal styles */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-overlay.show {
            display: flex;
        }
        
        .modal {
            background: #16213e;
            border-radius: 12px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal h2 {
            margin-bottom: 1rem;
        }
        
        .modal-close {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: none;
            border: none;
            color: #888;
            font-size: 1.5rem;
            cursor: pointer;
        }
        
        .category-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .category-item {
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            background: #0f0f23;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .category-item:hover {
            background: #4f46e5;
        }
        
        .category-item .count {
            color: #888;
            font-size: 0.8rem;
        }
        
        .new-category-form {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #333;
        }
        
        .new-category-form input {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            background: #0f0f23;
            color: #fff;
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .new-category-form button {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            background: #4f46e5;
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
        }
        
        .new-category-form button:hover {
            background: #4338ca;
        }
        
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #4f46e5;
            color: #fff;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s;
            z-index: 1001;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        .toast.error {
            background: #dc2626;
        }
        
        .toast.success {
            background: #059669;
        }
        
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: #666;
        }
        
        .empty-state h2 {
            margin-bottom: 1rem;
        }
        
        a.instagram-link {
            color: #e879f9;
            text-decoration: none;
            font-size: 0.7rem;
            display: block;
            margin-top: 0.25rem;
        }
        
        a.instagram-link:hover {
            text-decoration: underline;
        }
        
        .hidden {
            display: none !important;
        }
        
        /* Bulk selection */
        .video-card .checkbox {
            position: absolute;
            top: 8px;
            left: 8px;
            width: 24px;
            height: 24px;
            background: rgba(0,0,0,0.6);
            border: 2px solid #fff;
            border-radius: 4px;
            cursor: pointer;
            z-index: 5;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.2s;
        }
        
        .video-card:hover .checkbox,
        .video-card.checked .checkbox {
            opacity: 1;
        }
        
        .video-card.checked .checkbox {
            background: #4f46e5;
            border-color: #4f46e5;
        }
        
        .video-card.checked .checkbox::after {
            content: '✓';
            color: #fff;
            font-size: 14px;
            font-weight: bold;
        }
        
        .bulk-actions {
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: #1e1e3f;
            border: 1px solid #4f46e5;
            border-radius: 12px;
            padding: 1rem 1.5rem;
            display: none;
            align-items: center;
            gap: 1rem;
            z-index: 100;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        
        .bulk-actions.show {
            display: flex;
        }
        
        .bulk-actions .count {
            font-weight: bold;
            color: #4f46e5;
        }
        
        .bulk-actions button {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .bulk-actions .btn-bulk-exclude {
            background: #dc2626;
            color: #fff;
        }
        
        .bulk-actions .btn-bulk-move {
            background: #0891b2;
            color: #fff;
        }
        
        .bulk-actions .btn-bulk-clear {
            background: #374151;
            color: #fff;
        }
        
        .bulk-actions .btn-select-all {
            background: #4f46e5;
            color: #fff;
        }
        
        /* Video Preview Modal */
        .preview-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.95);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        
        .preview-modal.show {
            display: flex;
        }
        
        .preview-content {
            display: flex;
            gap: 2rem;
            max-width: 95vw;
            max-height: 95vh;
            padding: 1rem;
        }
        
        .preview-video-container {
            flex-shrink: 0;
        }
        
        .preview-video-container video {
            max-height: 85vh;
            max-width: 50vw;
            border-radius: 12px;
            background: #000;
        }
        
        .preview-info {
            width: 400px;
            max-height: 85vh;
            overflow-y: auto;
            background: #16213e;
            border-radius: 12px;
            padding: 1.5rem;
        }
        
        .preview-info h3 {
            margin-bottom: 0.5rem;
            color: #4f46e5;
        }
        
        .preview-info .shortcode {
            font-family: monospace;
            color: #888;
            margin-bottom: 1rem;
        }
        
        .preview-info .transcript {
            background: #0f0f23;
            padding: 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            line-height: 1.6;
            white-space: pre-wrap;
            max-height: 50vh;
            overflow-y: auto;
        }
        
        .preview-info .meta {
            margin-top: 1rem;
            font-size: 0.85rem;
            color: #888;
        }
        
        .preview-info .actions {
            margin-top: 1rem;
            display: flex;
            gap: 0.5rem;
            background: none;
            padding: 0;
        }
        
        .preview-close {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            font-size: 2rem;
            cursor: pointer;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .preview-close:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .preview-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            font-size: 2rem;
            cursor: pointer;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .preview-nav:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .preview-nav.prev {
            left: 1rem;
        }
        
        .preview-nav.next {
            right: 1rem;
        }
        
        /* Transcript in card */
        .video-card .transcript-preview {
            font-size: 0.7rem;
            color: #888;
            margin-top: 0.25rem;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            line-height: 1.3;
        }
        
        /* Stats Dashboard */
        .stats-dashboard {
            background: #16213e;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .stat-card {
            background: #0f0f23;
            padding: 1.25rem;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: #4f46e5;
        }
        
        .stat-card .label {
            font-size: 0.85rem;
            color: #888;
            margin-top: 0.25rem;
        }
        
        .stat-card.excluded .value {
            color: #f87171;
        }
        
        .stat-card.moved .value {
            color: #22d3ee;
        }
        
        .stat-card.keeping .value {
            color: #34d399;
        }
        
        .stats-chart {
            background: #0f0f23;
            border-radius: 8px;
            padding: 1rem;
        }
        
        .chart-bar {
            display: flex;
            align-items: center;
            margin: 0.5rem 0;
            gap: 0.5rem;
        }
        
        .chart-bar .name {
            width: 150px;
            font-size: 0.8rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .chart-bar .bar {
            flex: 1;
            height: 20px;
            background: #1e1e3f;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .chart-bar .fill {
            height: 100%;
            background: #4f46e5;
            border-radius: 4px;
            transition: width 0.3s;
        }
        
        .chart-bar .count {
            width: 50px;
            text-align: right;
            font-size: 0.8rem;
            color: #888;
        }
        
        /* Category management */
        .category-link .category-actions {
            display: none;
            gap: 0.25rem;
            margin-left: 0.5rem;
        }
        
        .category-link:hover .category-actions {
            display: flex;
        }
        
        .category-link .category-actions button {
            background: rgba(255,255,255,0.1);
            border: none;
            color: #888;
            font-size: 0.7rem;
            padding: 0.15rem 0.35rem;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .category-link .category-actions button:hover {
            background: rgba(255,255,255,0.2);
            color: #fff;
        }
        
        .category-link .category-actions .delete-btn:hover {
            background: #dc2626;
        }
        
        /* Rename modal */
        .rename-modal .modal {
            max-width: 400px;
        }
        
        .rename-modal input {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            background: #0f0f23;
            color: #fff;
            font-size: 1rem;
            margin-bottom: 1rem;
        }
        
        .rename-modal .btn-row {
            display: flex;
            gap: 0.5rem;
        }
        
        .rename-modal button {
            flex: 1;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
        }
        
        .rename-modal .btn-cancel {
            background: #374151;
            color: #fff;
        }
        
        .rename-modal .btn-confirm {
            background: #4f46e5;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <h1>📁 {{ category_name if category_name else 'Category Review' }}</h1>
        </div>
        <div class="header-stats">
            <span>Total: <strong>{{ total_videos }}</strong></span>
            <span class="auto-count">✓ Keeping: <strong id="keeping-count">{{ total_videos - excluded_count }}</strong></span>
            <span style="color: #f87171;">✗ Excluded: <strong id="excluded-count">{{ excluded_count }}</strong></span>
            <span style="color: #22d3ee;">↪ Moved: <strong id="moved-count">0</strong></span>
            {% if category_name %}
            <span style="color: #a78bfa;">📊 Progress: <strong id="progress-text">0</strong>/{{ total_videos }} reviewed</span>
            {% endif %}
        </div>
        {% if category_name %}
        <div class="progress-bar">
            <div class="progress" id="progress-bar" style="width: 0%"></div>
        </div>
        {% endif %}
        <div class="keyboard-hints">
            <kbd>X</kbd> Exclude
            <kbd>U</kbd> Undo
            <kbd>M</kbd> Move
            <kbd>Space</kbd> Toggle select
            <kbd>A</kbd> Select all
            <kbd>P</kbd> Preview
            <kbd>←</kbd><kbd>→</kbd> Navigate
            <kbd>Esc</kbd> Close
        </div>
    </div>
    
    <nav class="nav" id="category-nav">
        <a href="/" {% if not category_name %}class="active"{% endif %}>
            All Categories
        </a>
        {% for cat in categories %}
        <a href="/category/{{ cat.name | urlencode }}" 
           class="category-link {% if category_name == cat.name %}active{% endif %}"
           data-name="{{ cat.name }}"
           data-count="{{ cat.count }}">
            {{ cat.name }}<span class="count">{{ cat.count }}</span>
            <span class="category-actions" onclick="event.preventDefault(); event.stopPropagation();">
                <button onclick="showRenameModal('{{ cat.name }}')" title="Rename">✏️</button>
                <button class="delete-btn" onclick="deleteCategory('{{ cat.name }}')" title="Delete">🗑️</button>
            </span>
        </a>
        {% endfor %}
        <div class="nav-controls">
            <select class="nav-sort-select" id="nav-sort-select" onchange="sortCategoryNav()">
                <option value="count-desc">Categories: By Count ↓</option>
                <option value="count-asc">Categories: By Count ↑</option>
                <option value="alpha-asc">Categories: A-Z</option>
                <option value="alpha-desc">Categories: Z-A</option>
            </select>
            <button class="add-category-btn" onclick="showAddCategoryModal()">+ Add Category</button>
        </div>
    </nav>
    
    <div class="container">
        {% if show_stats and stats %}
        <!-- Statistics Dashboard -->
        <div class="stats-dashboard">
            <h2 style="margin-bottom: 1rem;">📊 Review Progress</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{{ stats.total }}</div>
                    <div class="label">Total Videos</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ stats.categories_count }}</div>
                    <div class="label">Categories</div>
                </div>
                <div class="stat-card keeping">
                    <div class="value">{{ stats.keeping }}</div>
                    <div class="label">Keeping</div>
                </div>
                <div class="stat-card excluded">
                    <div class="value">{{ stats.excluded }}</div>
                    <div class="label">Excluded</div>
                </div>
                <div class="stat-card moved">
                    <div class="value">{{ stats.moved }}</div>
                    <div class="label">Moved</div>
                </div>
                <div class="stat-card">
                    <div class="value">{{ stats.review_percent }}%</div>
                    <div class="label">Reviewed</div>
                </div>
            </div>
            
            <h3 style="margin: 1.5rem 0 1rem;">Top Categories</h3>
            <div class="stats-chart">
                {% for cat in categories[:10] %}
                <div class="chart-bar">
                    <div class="name"><a href="/category/{{ cat.name | urlencode }}" style="color: #fff; text-decoration: none;">{{ cat.name }}</a></div>
                    <div class="bar">
                        <div class="fill" style="width: {{ (cat.count / stats.total * 100) if stats.total > 0 else 0 }}%"></div>
                    </div>
                    <div class="count">{{ cat.count }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if videos %}
        <div class="toolbar">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="🔍 Search keywords, shortcode..." onkeyup="filterVideos()">
            </div>
            <select class="sort-select" id="sort-select" onchange="sortVideos()">
                <option value="score-desc">Score: High → Low</option>
                <option value="score-asc">Score: Low → High</option>
                <option value="shortcode">Shortcode A-Z</option>
            </select>
            <div class="filter-group">
                <label>
                    <input type="checkbox" id="hide-excluded" checked onchange="filterVideos()">
                    Hide excluded
                </label>
                <label>
                    <input type="checkbox" id="show-only-excluded" onchange="filterVideos()">
                    Only excluded
                </label>
            </div>
        </div>
        
        <div class="grid" id="video-grid">
            {% for video in videos %}
            <div class="video-card {% if video.excluded %}excluded{% endif %} {% if video.moved_to %}moved{% endif %}" 
                 data-shortcode="{{ video.shortcode }}"
                 data-score="{{ video.score }}"
                 data-excluded="{{ video.excluded | lower }}"
                 data-moved="{{ video.moved_to or '' }}"
                 data-category="{{ video.category }}"
                 data-keywords="{{ video.keywords | join(' ') | lower }}"
                 data-transcript="{{ video.transcript | e if video.transcript else '' }}"
                 onclick="selectCard(this)">
                <div class="checkbox" onclick="event.stopPropagation(); toggleCheck(this.parentElement);"></div>
                <img src="/thumbnail/{{ video.shortcode }}" 
                     alt="{{ video.shortcode }}"
                     loading="lazy"
                     onclick="event.stopPropagation(); openPreview('{{ video.shortcode }}')"
                     onerror="this.style.background='#333'; this.style.display='block';">
                <div class="info">
                    <div class="shortcode">{{ video.shortcode }}</div>
                    <div class="score">Score: {{ video.score }}{% if video.moved_to %} → {{ video.moved_to }}{% endif %}</div>
                    <div class="keywords">{{ video.keywords | join(', ') }}</div>
                    {% if video.transcript %}
                    <div class="transcript-preview">{{ video.transcript[:100] }}{% if video.transcript|length > 100 %}...{% endif %}</div>
                    {% endif %}
                    <a href="https://www.instagram.com/reel/{{ video.shortcode }}" 
                       target="_blank" 
                       class="instagram-link"
                       onclick="event.stopPropagation()">
                        View on Instagram ↗
                    </a>
                </div>
                <div class="actions" onclick="event.stopPropagation()">
                    {% if video.excluded %}
                    <button class="btn-undo" onclick="undoAction('{{ video.shortcode }}', '{{ video.category }}')">
                        ↺ Undo
                    </button>
                    {% else %}
                    <button class="btn-exclude" onclick="excludeVideo('{{ video.shortcode }}', '{{ video.category }}')">
                        ✗ Exclude
                    </button>
                    <button class="btn-move" onclick="showMoveModal('{{ video.shortcode }}', '{{ video.category }}')">
                        ↪ Move
                    </button>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h2>No videos in this category</h2>
            <p>Select a category from the navigation above.</p>
        </div>
        {% endif %}
    </div>
    
    <!-- Move Modal -->
    <div class="modal-overlay" id="move-modal">
        <div class="modal">
            <h2>Move to Category</h2>
            <p style="color: #888; margin-bottom: 0.5rem;">Moving: <strong id="move-shortcode"></strong></p>
            <div class="modal-search">
                <input type="text" id="category-search" placeholder="🔍 Type to filter categories..." onkeyup="filterCategoryList()">
            </div>
            <div class="modal-sort-controls">
                <button class="modal-sort-btn active" id="modal-sort-count" onclick="sortCategoryList('count')">By Count</button>
                <button class="modal-sort-btn" id="modal-sort-alpha" onclick="sortCategoryList('alpha')">A-Z</button>
            </div>
            <div class="category-list" id="category-list">
                {% for cat in categories %}
                <div class="category-item" data-name="{{ cat.name }}" data-count="{{ cat.count }}" onclick="moveToCategory('{{ cat.name }}')">
                    <span class="cat-name">{{ cat.name }}</span>
                    <span class="count">{{ cat.count }}</span>
                </div>
                {% endfor %}
            </div>
            <div class="new-category-form">
                <input type="text" id="new-category-name" placeholder="Or create new category...">
                <button onclick="moveToNewCategory()">Create & Move</button>
            </div>
        </div>
    </div>
    
    <!-- Add Category Modal -->
    <div class="modal-overlay" id="add-category-modal">
        <div class="modal">
            <h2>Add New Category</h2>
            <div class="new-category-form" style="border: none; padding-top: 0; margin-top: 0;">
                <input type="text" id="add-category-name" placeholder="Category name...">
                <button onclick="addNewCategory()">Create Category</button>
            </div>
        </div>
    </div>
    
    <!-- Rename Category Modal -->
    <div class="modal-overlay rename-modal" id="rename-modal">
        <div class="modal">
            <h2>Rename Category</h2>
            <p style="color: #888; margin-bottom: 1rem;">Renaming: <strong id="rename-old-name"></strong></p>
            <input type="text" id="rename-new-name" placeholder="New category name...">
            <div class="btn-row">
                <button class="btn-cancel" onclick="hideRenameModal()">Cancel</button>
                <button class="btn-confirm" onclick="confirmRename()">Rename</button>
            </div>
        </div>
    </div>
    
    <!-- Video Preview Modal -->
    <div class="preview-modal" id="preview-modal">
        <button class="preview-close" onclick="closePreview()">×</button>
        <button class="preview-nav prev" onclick="navigatePreview('prev')">‹</button>
        <button class="preview-nav next" onclick="navigatePreview('next')">›</button>
        <div class="preview-content">
            <div class="preview-video-container">
                <video id="preview-video" controls autoplay>
                    <source id="preview-source" src="" type="video/mp4">
                </video>
            </div>
            <div class="preview-info">
                <h3>Video Details</h3>
                <div class="shortcode" id="preview-shortcode"></div>
                <div class="meta">
                    <p><strong>Category:</strong> <span id="preview-category"></span></p>
                    <p><strong>Score:</strong> <span id="preview-score"></span></p>
                    <p><strong>Keywords:</strong> <span id="preview-keywords"></span></p>
                </div>
                <h3 style="margin-top: 1.5rem;">Transcript</h3>
                <div class="transcript" id="preview-transcript">No transcript available</div>
                <div class="actions" id="preview-actions"></div>
            </div>
        </div>
    </div>
    
    <!-- Bulk Move Modal -->
    <div class="modal-overlay" id="bulk-move-modal">
        <div class="modal">
            <h2>Move Selected Videos</h2>
            <p style="color: #888; margin-bottom: 0.5rem;">Moving <strong id="bulk-move-count">0</strong> videos</p>
            <div class="modal-search">
                <input type="text" id="bulk-category-search" placeholder="🔍 Type to filter categories..." onkeyup="filterBulkCategoryList()">
            </div>
            <div class="category-list" id="bulk-category-list">
                {% for cat in categories %}
                <div class="category-item" data-name="{{ cat.name }}" data-count="{{ cat.count }}" onclick="bulkMoveToCategory('{{ cat.name }}')">
                    <span class="cat-name">{{ cat.name }}</span>
                    <span class="count">{{ cat.count }}</span>
                </div>
                {% endfor %}
            </div>
            <div class="new-category-form">
                <input type="text" id="bulk-new-category-name" placeholder="Or create new category...">
                <button onclick="bulkMoveToNewCategory()">Create & Move All</button>
            </div>
        </div>
    </div>
    
    <!-- Bulk Actions Bar -->
    <div class="bulk-actions" id="bulk-actions">
        <span><span class="count" id="bulk-count">0</span> selected</span>
        <button class="btn-select-all" onclick="selectAllVisible()">Select All</button>
        <button class="btn-bulk-exclude" onclick="bulkExclude()">Exclude All</button>
        <button class="btn-bulk-move" onclick="showBulkMoveModal()">Move All</button>
        <button class="btn-bulk-clear" onclick="clearSelection()">Clear</button>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        let selectedCard = null;
        let moveShortcode = null;
        let moveFromCategory = null;
        const allCategories = {{ categories | tojson }};
        
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show ' + type;
            setTimeout(() => {
                toast.className = 'toast';
            }, 2000);
        }
        
        function selectCard(card, scroll = true) {
            if (selectedCard) {
                selectedCard.classList.remove('selected');
            }
            selectedCard = card;
            card.classList.add('selected');
            if (scroll) {
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        function navigateCards(direction) {
            const cards = Array.from(document.querySelectorAll('.video-card:not(.hidden)'));
            if (cards.length === 0) return;
            
            let currentIndex = selectedCard ? cards.indexOf(selectedCard) : -1;
            let newIndex;
            
            if (direction === 'next') {
                newIndex = currentIndex < cards.length - 1 ? currentIndex + 1 : 0;
            } else {
                newIndex = currentIndex > 0 ? currentIndex - 1 : cards.length - 1;
            }
            
            selectCard(cards[newIndex]);
        }
        
        async function excludeVideo(shortcode, category) {
            try {
                const response = await fetch('/api/exclude', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ shortcode, category })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const card = document.querySelector(`[data-shortcode="${shortcode}"]`);
                    if (card) {
                        card.dataset.excluded = 'true';
                        card.classList.add('excluded');
                        updateCardButtons(card, true, false);
                        
                        if (document.getElementById('hide-excluded').checked) {
                            // Find next visible card before hiding
                            const cards = Array.from(document.querySelectorAll('.video-card:not(.hidden)'));
                            const currentIndex = cards.indexOf(card);
                            const nextCard = cards[currentIndex + 1] || cards[currentIndex - 1];
                            
                            card.classList.add('hidden');
                            
                            if (nextCard && selectedCard === card) {
                                selectCard(nextCard, false);
                            }
                        }
                    }
                    updateCounts();
                    showToast(`Excluded: ${shortcode}`, 'error');
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        async function undoAction(shortcode, category) {
            try {
                const response = await fetch('/api/undo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ shortcode, category })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const card = document.querySelector(`[data-shortcode="${shortcode}"]`);
                    if (card) {
                        card.dataset.excluded = 'false';
                        card.dataset.moved = '';
                        card.classList.remove('excluded', 'moved', 'hidden');
                        updateCardButtons(card, false, false);
                        
                        // Update score display
                        const scoreEl = card.querySelector('.score');
                        if (scoreEl) {
                            scoreEl.textContent = `Score: ${card.dataset.score}`;
                        }
                    }
                    updateCounts();
                    showToast(`Restored: ${shortcode}`, 'success');
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        function updateCardButtons(card, isExcluded, isMoved) {
            const actions = card.querySelector('.actions');
            const shortcode = card.dataset.shortcode;
            const category = card.dataset.category;
            
            if (isExcluded || isMoved) {
                actions.innerHTML = `
                    <button class="btn-undo" onclick="undoAction('${shortcode}', '${category}')">
                        ↺ Undo
                    </button>
                `;
            } else {
                actions.innerHTML = `
                    <button class="btn-exclude" onclick="excludeVideo('${shortcode}', '${category}')">
                        ✗ Exclude
                    </button>
                    <button class="btn-move" onclick="showMoveModal('${shortcode}', '${category}')">
                        ↪ Move
                    </button>
                `;
            }
        }
        
        function showMoveModal(shortcode, fromCategory) {
            moveShortcode = shortcode;
            moveFromCategory = fromCategory;
            document.getElementById('move-shortcode').textContent = shortcode;
            document.getElementById('move-modal').classList.add('show');
            document.getElementById('new-category-name').value = '';
            document.getElementById('category-search').value = '';
            filterCategoryList();
            document.getElementById('category-search').focus();
        }
        
        function hideMoveModal() {
            document.getElementById('move-modal').classList.remove('show');
            moveShortcode = null;
            moveFromCategory = null;
        }
        
        function filterCategoryList() {
            const searchTerm = document.getElementById('category-search').value.toLowerCase();
            const items = document.querySelectorAll('#category-list .category-item');
            
            items.forEach(item => {
                const name = item.dataset.name.toLowerCase();
                if (name.includes(searchTerm)) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        }
        
        function sortCategoryList(sortBy) {
            const list = document.getElementById('category-list');
            const items = Array.from(list.querySelectorAll('.category-item'));
            
            // Update button states
            document.getElementById('modal-sort-count').classList.toggle('active', sortBy === 'count');
            document.getElementById('modal-sort-alpha').classList.toggle('active', sortBy === 'alpha');
            
            items.sort((a, b) => {
                if (sortBy === 'count') {
                    return parseInt(b.dataset.count) - parseInt(a.dataset.count);
                } else {
                    return a.dataset.name.localeCompare(b.dataset.name);
                }
            });
            
            items.forEach(item => list.appendChild(item));
        }
        
        function sortCategoryNav() {
            const sortBy = document.getElementById('nav-sort-select').value;
            const nav = document.getElementById('category-nav');
            const links = Array.from(nav.querySelectorAll('a.category-link'));
            const controls = nav.querySelector('.nav-controls');
            const allLink = nav.querySelector('a:not(.category-link)');
            
            links.sort((a, b) => {
                const nameA = a.dataset.name;
                const nameB = b.dataset.name;
                const countA = parseInt(a.dataset.count);
                const countB = parseInt(b.dataset.count);
                
                switch (sortBy) {
                    case 'count-desc':
                        return countB - countA;
                    case 'count-asc':
                        return countA - countB;
                    case 'alpha-asc':
                        return nameA.localeCompare(nameB);
                    case 'alpha-desc':
                        return nameB.localeCompare(nameA);
                    default:
                        return 0;
                }
            });
            
            // Rebuild nav: All Categories link, then sorted links, then controls
            links.forEach(link => nav.insertBefore(link, controls));
        }
        
        function showAddCategoryModal() {
            document.getElementById('add-category-modal').classList.add('show');
            document.getElementById('add-category-name').value = '';
            document.getElementById('add-category-name').focus();
        }
        
        function hideAddCategoryModal() {
            document.getElementById('add-category-modal').classList.remove('show');
        }
        
        async function moveToCategory(targetCategory) {
            if (!moveShortcode) return;
            
            try {
                const response = await fetch('/api/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        shortcode: moveShortcode, 
                        from_category: moveFromCategory,
                        to_category: targetCategory 
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const card = document.querySelector(`[data-shortcode="${moveShortcode}"]`);
                    if (card) {
                        card.dataset.moved = targetCategory;
                        card.classList.add('moved');
                        updateCardButtons(card, false, true);
                        
                        // Update score display to show new category
                        const scoreEl = card.querySelector('.score');
                        if (scoreEl) {
                            scoreEl.textContent = `Score: ${card.dataset.score} → ${targetCategory}`;
                        }
                    }
                    updateCounts();
                    hideMoveModal();
                    showToast(`Moved to: ${targetCategory}`, 'success');
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        async function moveToNewCategory() {
            const newName = document.getElementById('new-category-name').value.trim();
            if (!newName) {
                showToast('Please enter a category name', 'error');
                return;
            }
            await moveToCategory(newName);
        }
        
        async function addNewCategory() {
            const newName = document.getElementById('add-category-name').value.trim();
            if (!newName) {
                showToast('Please enter a category name', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/add-category', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: newName })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    hideAddCategoryModal();
                    showToast(`Created: ${newName}`, 'success');
                    // Reload to show new category
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        function updateCounts() {
            const cards = document.querySelectorAll('.video-card');
            let excluded = 0, moved = 0;
            cards.forEach(card => {
                if (card.dataset.excluded === 'true') excluded++;
                if (card.dataset.moved) moved++;
            });
            document.getElementById('excluded-count').textContent = excluded;
            document.getElementById('moved-count').textContent = moved;
            document.getElementById('keeping-count').textContent = cards.length - excluded;
            
            // Update progress
            const reviewed = excluded + moved;
            const progressText = document.getElementById('progress-text');
            const progressBar = document.getElementById('progress-bar');
            if (progressText) {
                progressText.textContent = reviewed;
            }
            if (progressBar) {
                const percent = (reviewed / cards.length) * 100;
                progressBar.style.width = percent + '%';
            }
        }
        
        function filterVideos() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const hideExcluded = document.getElementById('hide-excluded').checked;
            const showOnlyExcluded = document.getElementById('show-only-excluded').checked;
            
            // Uncheck conflicting filters
            if (showOnlyExcluded && hideExcluded) {
                document.getElementById('hide-excluded').checked = false;
            }
            
            document.querySelectorAll('.video-card').forEach(card => {
                const shortcode = card.dataset.shortcode.toLowerCase();
                const keywords = card.dataset.keywords;
                const isExcluded = card.dataset.excluded === 'true';
                
                let show = true;
                
                // Search filter
                if (searchTerm && !shortcode.includes(searchTerm) && !keywords.includes(searchTerm)) {
                    show = false;
                }
                
                // Excluded filter
                if (showOnlyExcluded && !isExcluded) {
                    show = false;
                } else if (hideExcluded && isExcluded) {
                    show = false;
                }
                
                card.classList.toggle('hidden', !show);
            });
        }
        
        function sortVideos() {
            const sortBy = document.getElementById('sort-select').value;
            const grid = document.getElementById('video-grid');
            const cards = Array.from(grid.querySelectorAll('.video-card'));
            
            cards.sort((a, b) => {
                switch (sortBy) {
                    case 'score-desc':
                        return parseInt(b.dataset.score) - parseInt(a.dataset.score);
                    case 'score-asc':
                        return parseInt(a.dataset.score) - parseInt(b.dataset.score);
                    case 'shortcode':
                        return a.dataset.shortcode.localeCompare(b.dataset.shortcode);
                    default:
                        return 0;
                }
            });
            
            cards.forEach(card => grid.appendChild(card));
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Skip if typing in input
            if (e.target.tagName === 'INPUT') {
                if (e.key === 'Escape') {
                    e.target.blur();
                    closeAllModals();
                }
                return;
            }
            
            switch (e.key.toLowerCase()) {
                case 'x':
                    if (selectedCard && selectedCard.dataset.excluded !== 'true') {
                        excludeVideo(selectedCard.dataset.shortcode, selectedCard.dataset.category);
                    }
                    break;
                case 'u':
                    if (selectedCard && (selectedCard.dataset.excluded === 'true' || selectedCard.dataset.moved)) {
                        undoAction(selectedCard.dataset.shortcode, selectedCard.dataset.category);
                    }
                    break;
                case 'm':
                    if (selectedCard && selectedCard.dataset.excluded !== 'true') {
                        showMoveModal(selectedCard.dataset.shortcode, selectedCard.dataset.category);
                    }
                    break;
                case ' ':
                    e.preventDefault();
                    if (selectedCard) toggleCheck(selectedCard);
                    break;
                case 'a':
                    e.preventDefault();
                    selectAllVisible();
                    break;
                case 'p':
                    if (selectedCard) {
                        openPreview(selectedCard.dataset.shortcode);
                    }
                    break;
                case 'arrowleft':
                    e.preventDefault();
                    if (document.getElementById('preview-modal').classList.contains('show')) {
                        navigatePreview('prev');
                    } else {
                        navigateCards('prev');
                    }
                    break;
                case 'arrowright':
                    e.preventDefault();
                    if (document.getElementById('preview-modal').classList.contains('show')) {
                        navigatePreview('next');
                    } else {
                        navigateCards('next');
                    }
                    break;
                case 'escape':
                    closeAllModals();
                    break;
            }
        });
        
        function closeAllModals() {
            hideMoveModal();
            hideAddCategoryModal();
            hideRenameModal();
            hideBulkMoveModal();
            closePreview();
        }
        
        // === BULK SELECTION ===
        function toggleCheck(card) {
            card.classList.toggle('checked');
            updateBulkActions();
        }
        
        function getCheckedCards() {
            return Array.from(document.querySelectorAll('.video-card.checked:not(.hidden)'));
        }
        
        function updateBulkActions() {
            const checked = getCheckedCards();
            const bulkActions = document.getElementById('bulk-actions');
            const bulkCount = document.getElementById('bulk-count');
            
            if (checked.length > 0) {
                bulkActions.classList.add('show');
                bulkCount.textContent = checked.length;
            } else {
                bulkActions.classList.remove('show');
            }
        }
        
        function selectAllVisible() {
            const cards = document.querySelectorAll('.video-card:not(.hidden):not(.excluded)');
            const allChecked = Array.from(cards).every(c => c.classList.contains('checked'));
            
            cards.forEach(card => {
                if (allChecked) {
                    card.classList.remove('checked');
                } else {
                    card.classList.add('checked');
                }
            });
            updateBulkActions();
        }
        
        function clearSelection() {
            document.querySelectorAll('.video-card.checked').forEach(card => {
                card.classList.remove('checked');
            });
            updateBulkActions();
        }
        
        async function bulkExclude() {
            const checked = getCheckedCards();
            if (checked.length === 0) return;
            
            if (!confirm(`Exclude ${checked.length} videos?`)) return;
            
            let success = 0, failed = 0;
            
            for (const card of checked) {
                try {
                    const response = await fetch('/api/exclude', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            shortcode: card.dataset.shortcode, 
                            category: card.dataset.category 
                        })
                    });
                    const data = await response.json();
                    if (data.success) {
                        card.dataset.excluded = 'true';
                        card.classList.add('excluded');
                        card.classList.remove('checked');
                        updateCardButtons(card, true, false);
                        if (document.getElementById('hide-excluded').checked) {
                            card.classList.add('hidden');
                        }
                        success++;
                    } else {
                        failed++;
                    }
                } catch (err) {
                    failed++;
                }
            }
            
            updateCounts();
            updateBulkActions();
            showToast(`Excluded ${success} videos` + (failed > 0 ? `, ${failed} failed` : ''), failed > 0 ? 'error' : 'success');
        }
        
        function showBulkMoveModal() {
            const checked = getCheckedCards();
            if (checked.length === 0) return;
            
            document.getElementById('bulk-move-count').textContent = checked.length;
            document.getElementById('bulk-move-modal').classList.add('show');
            document.getElementById('bulk-category-search').value = '';
            filterBulkCategoryList();
            document.getElementById('bulk-category-search').focus();
        }
        
        function hideBulkMoveModal() {
            document.getElementById('bulk-move-modal').classList.remove('show');
        }
        
        function filterBulkCategoryList() {
            const searchTerm = document.getElementById('bulk-category-search').value.toLowerCase();
            const items = document.querySelectorAll('#bulk-category-list .category-item');
            
            items.forEach(item => {
                const name = item.dataset.name.toLowerCase();
                if (name.includes(searchTerm)) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        }
        
        async function bulkMoveToCategory(targetCategory) {
            const checked = getCheckedCards();
            if (checked.length === 0) return;
            
            let success = 0, failed = 0;
            
            for (const card of checked) {
                try {
                    const response = await fetch('/api/move', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            shortcode: card.dataset.shortcode, 
                            from_category: card.dataset.category,
                            to_category: targetCategory 
                        })
                    });
                    const data = await response.json();
                    if (data.success) {
                        card.dataset.moved = targetCategory;
                        card.classList.add('moved');
                        card.classList.remove('checked');
                        updateCardButtons(card, false, true);
                        const scoreEl = card.querySelector('.score');
                        if (scoreEl) {
                            scoreEl.textContent = `Score: ${card.dataset.score} → ${targetCategory}`;
                        }
                        success++;
                    } else {
                        failed++;
                    }
                } catch (err) {
                    failed++;
                }
            }
            
            updateCounts();
            updateBulkActions();
            hideBulkMoveModal();
            showToast(`Moved ${success} videos to ${targetCategory}` + (failed > 0 ? `, ${failed} failed` : ''), failed > 0 ? 'error' : 'success');
        }
        
        async function bulkMoveToNewCategory() {
            const newName = document.getElementById('bulk-new-category-name').value.trim();
            if (!newName) {
                showToast('Please enter a category name', 'error');
                return;
            }
            await bulkMoveToCategory(newName);
        }
        
        // === VIDEO PREVIEW ===
        let currentPreviewShortcode = null;
        
        async function openPreview(shortcode) {
            currentPreviewShortcode = shortcode;
            const modal = document.getElementById('preview-modal');
            const video = document.getElementById('preview-video');
            const source = document.getElementById('preview-source');
            
            // Set video source
            source.src = `/video/${shortcode}`;
            video.load();
            
            // Get card data
            const card = document.querySelector(`[data-shortcode="${shortcode}"]`);
            if (card) {
                document.getElementById('preview-shortcode').textContent = shortcode;
                document.getElementById('preview-category').textContent = card.dataset.category || 'None';
                document.getElementById('preview-score').textContent = card.dataset.score || '0';
                document.getElementById('preview-keywords').textContent = card.dataset.keywords || 'None';
                
                const transcript = card.dataset.transcript || 'No transcript available';
                document.getElementById('preview-transcript').textContent = transcript;
                
                // Update action buttons
                const actions = document.getElementById('preview-actions');
                const isExcluded = card.dataset.excluded === 'true';
                const category = card.dataset.category;
                
                if (isExcluded) {
                    actions.innerHTML = `
                        <button class="btn-undo" onclick="undoAction('${shortcode}', '${category}'); updatePreviewActions();">
                            ↺ Undo Exclude
                        </button>
                    `;
                } else {
                    actions.innerHTML = `
                        <button class="btn-exclude" onclick="excludeVideo('${shortcode}', '${category}'); updatePreviewActions();">
                            ✗ Exclude
                        </button>
                        <button class="btn-move" onclick="closePreview(); showMoveModal('${shortcode}', '${category}');">
                            ↪ Move
                        </button>
                    `;
                }
            }
            
            modal.classList.add('show');
        }
        
        function updatePreviewActions() {
            if (currentPreviewShortcode) {
                setTimeout(() => openPreview(currentPreviewShortcode), 100);
            }
        }
        
        function closePreview() {
            const modal = document.getElementById('preview-modal');
            const video = document.getElementById('preview-video');
            video.pause();
            modal.classList.remove('show');
            currentPreviewShortcode = null;
        }
        
        function navigatePreview(direction) {
            if (!currentPreviewShortcode) return;
            
            const cards = Array.from(document.querySelectorAll('.video-card:not(.hidden)'));
            const currentIndex = cards.findIndex(c => c.dataset.shortcode === currentPreviewShortcode);
            
            let newIndex;
            if (direction === 'next') {
                newIndex = currentIndex < cards.length - 1 ? currentIndex + 1 : 0;
            } else {
                newIndex = currentIndex > 0 ? currentIndex - 1 : cards.length - 1;
            }
            
            const newCard = cards[newIndex];
            if (newCard) {
                selectCard(newCard, false);
                openPreview(newCard.dataset.shortcode);
            }
        }
        
        // === CATEGORY MANAGEMENT ===
        let renamingCategory = null;
        
        function showRenameModal(categoryName) {
            renamingCategory = categoryName;
            document.getElementById('rename-old-name').textContent = categoryName;
            document.getElementById('rename-new-name').value = categoryName;
            document.getElementById('rename-modal').classList.add('show');
            document.getElementById('rename-new-name').focus();
            document.getElementById('rename-new-name').select();
        }
        
        function hideRenameModal() {
            document.getElementById('rename-modal').classList.remove('show');
            renamingCategory = null;
        }
        
        async function confirmRename() {
            if (!renamingCategory) return;
            
            const newName = document.getElementById('rename-new-name').value.trim();
            if (!newName) {
                showToast('Please enter a category name', 'error');
                return;
            }
            
            if (newName === renamingCategory) {
                hideRenameModal();
                return;
            }
            
            try {
                const response = await fetch('/api/rename-category', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        old_name: renamingCategory, 
                        new_name: newName 
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    hideRenameModal();
                    showToast(`Renamed to: ${newName}`, 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        async function deleteCategory(categoryName) {
            if (!confirm(`Delete category "${categoryName}"?\\n\\nThis will NOT delete the videos, only remove them from this category.`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/delete-category', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: categoryName })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(`Deleted: ${categoryName}`, 'success');
                    setTimeout(() => {
                        if (window.location.pathname.includes(encodeURIComponent(categoryName))) {
                            window.location.href = '/';
                        } else {
                            location.reload();
                        }
                    }, 500);
                } else {
                    showToast('Error: ' + data.error, 'error');
                }
            } catch (err) {
                showToast('Network error', 'error');
            }
        }
        
        // Click outside modal to close
        document.getElementById('move-modal').addEventListener('click', (e) => {
            if (e.target.id === 'move-modal') hideMoveModal();
        });
        document.getElementById('add-category-modal').addEventListener('click', (e) => {
            if (e.target.id === 'add-category-modal') hideAddCategoryModal();
        });
        document.getElementById('rename-modal').addEventListener('click', (e) => {
            if (e.target.id === 'rename-modal') hideRenameModal();
        });
        document.getElementById('bulk-move-modal').addEventListener('click', (e) => {
            if (e.target.id === 'bulk-move-modal') hideBulkMoveModal();
        });
        document.getElementById('preview-modal').addEventListener('click', (e) => {
            if (e.target.id === 'preview-modal') closePreview();
        });
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            filterVideos();
            updateCounts();
            
            // Select first card
            const firstCard = document.querySelector('.video-card:not(.hidden)');
            if (firstCard) selectCard(firstCard);
        });
    </script>
</body>
</html>
'''


def find_thumbnail(shortcode: str) -> str | None:
    """Find the thumbnail image for a video."""
    video_dir = Path(REEL_ARCHIVE_DIR) / shortcode
    
    if not video_dir.exists():
        return None
    
    # Look for jpg files with the shortcode in the name
    for pattern in [f"*{shortcode}*.jpg", f"*{shortcode}*.jpeg", "*.jpg", "*.jpeg"]:
        matches = list(video_dir.glob(pattern))
        if matches:
            return str(matches[0])
    
    return None


def load_categories() -> dict:
    """Load all categories from categories.json."""
    categories_file = Path(REEL_ARCHIVE_DIR) / "categories.json"
    
    if not categories_file.exists():
        return {}
    
    with open(categories_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_categories(data: dict) -> bool:
    """Save categories to categories.json."""
    categories_file = Path(REEL_ARCHIVE_DIR) / "categories.json"
    
    try:
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving categories: {e}")
        return False


def load_video_category(shortcode: str) -> dict:
    """Load category info for a specific video."""
    category_file = Path(REEL_ARCHIVE_DIR) / shortcode / "category.json"
    
    if not category_file.exists():
        return {}
    
    with open(category_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_video_category(shortcode: str, data: dict) -> bool:
    """Save category info for a specific video."""
    category_file = Path(REEL_ARCHIVE_DIR) / shortcode / "category.json"
    
    try:
        with open(category_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {category_file}: {e}")
        return False


@app.route('/')
def index():
    """Show all categories overview with statistics dashboard."""
    categories_data = load_categories()
    
    # Build category list with counts (fast - no per-video scan)
    categories = []
    total_videos = 0
    total_manual = 0
    
    for name, data in sorted(categories_data.items(), key=lambda x: len(x[1].get('videos', [])), reverse=True):
        videos_in_cat = data.get('videos', [])
        manual_count = sum(1 for v in videos_in_cat if v.get('manual', False))
        total_manual += manual_count
        
        categories.append({
            'name': name,
            'count': len(videos_in_cat),
            'excluded': 0,  # Not computed on home for speed
            'moved': 0
        })
        total_videos += len(videos_in_cat)
    
    # Simple stats (don't scan individual files for speed)
    stats = {
        'total': total_videos,
        'reviewed': total_manual,
        'excluded': 0,
        'moved': 0,
        'keeping': total_videos,
        'manual': total_manual,
        'categories_count': len(categories),
        'review_percent': round((total_manual / total_videos * 100) if total_videos > 0 else 0, 1)
    }
    
    return render_template_string(
        HTML_TEMPLATE,
        categories=categories,
        category_name=None,
        videos=[],
        total_videos=total_videos,
        excluded_count=0,
        stats=stats,
        show_stats=True
    )


@app.route('/category/<path:category_name>')
def category_view(category_name: str):
    """Show videos in a specific category."""
    categories_data = load_categories()
    
    # Build category list for navigation
    categories = []
    for name, data in sorted(categories_data.items(), key=lambda x: len(x[1].get('videos', [])), reverse=True):
        categories.append({
            'name': name,
            'count': len(data.get('videos', []))
        })
    
    # Get videos for this category
    category_data = categories_data.get(category_name, {})
    videos_raw = category_data.get('videos', [])
    
    # Build video list with current status
    videos = []
    excluded_count = 0
    
    for v in videos_raw:
        shortcode = v.get('shortcode', '')
        
        # Load current status from individual category.json
        video_data = load_video_category(shortcode)
        is_excluded = video_data.get('excluded', False)
        moved_to = video_data.get('moved_to', None)
        
        # Load transcript
        transcript = load_transcript(shortcode)
        
        if is_excluded:
            excluded_count += 1
        
        videos.append({
            'shortcode': shortcode,
            'score': v.get('score', 0),
            'keywords': v.get('matched_keywords', []),
            'excluded': is_excluded,
            'moved_to': moved_to,
            'category': category_name,
            'transcript': transcript
        })
    
    return render_template_string(
        HTML_TEMPLATE,
        categories=categories,
        category_name=category_name,
        videos=videos,
        total_videos=len(videos),
        excluded_count=excluded_count
    )


@app.route('/thumbnail/<shortcode>')
def serve_thumbnail(shortcode: str):
    """Serve the thumbnail image for a video."""
    thumbnail_path = find_thumbnail(shortcode)
    
    if thumbnail_path:
        directory = os.path.dirname(thumbnail_path)
        filename = os.path.basename(thumbnail_path)
        return send_from_directory(directory, filename)
    
    # Return a placeholder if no image found
    return '', 404


@app.route('/api/exclude', methods=['POST'])
def api_exclude():
    """API endpoint to exclude a video from its category."""
    data = request.get_json()
    
    shortcode = data.get('shortcode')
    category = data.get('category')
    
    if not shortcode:
        return jsonify({'success': False, 'error': 'Missing shortcode'})
    
    # Load existing data
    video_data = load_video_category(shortcode)
    
    if not video_data:
        video_data = {
            'shortcode': shortcode,
            'url': f"https://www.instagram.com/reel/{shortcode}"
        }
    
    # Mark as excluded and remove category
    video_data['excluded'] = True
    video_data['excluded_from'] = category
    video_data['category'] = None
    video_data['manual'] = True
    
    if save_video_category(shortcode, video_data):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


@app.route('/api/undo', methods=['POST'])
def api_undo():
    """API endpoint to undo exclusion or move."""
    data = request.get_json()
    
    shortcode = data.get('shortcode')
    category = data.get('category')
    
    if not shortcode:
        return jsonify({'success': False, 'error': 'Missing shortcode'})
    
    video_data = load_video_category(shortcode)
    
    if video_data:
        video_data['excluded'] = False
        video_data['category'] = category
        video_data['manual'] = False
        
        # Remove move/exclude tracking
        for key in ['excluded_from', 'moved_to', 'moved_from']:
            if key in video_data:
                del video_data[key]
        
        if save_video_category(shortcode, video_data):
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Failed to save'})


@app.route('/api/move', methods=['POST'])
def api_move():
    """API endpoint to move a video to a different category."""
    data = request.get_json()
    
    shortcode = data.get('shortcode')
    from_category = data.get('from_category')
    to_category = data.get('to_category')
    
    if not shortcode or not to_category:
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    # Load existing data
    video_data = load_video_category(shortcode)
    
    if not video_data:
        video_data = {
            'shortcode': shortcode,
            'url': f"https://www.instagram.com/reel/{shortcode}"
        }
    
    # Update category
    video_data['category'] = to_category
    video_data['moved_from'] = from_category
    video_data['moved_to'] = to_category
    video_data['manual'] = True
    video_data['excluded'] = False
    
    if save_video_category(shortcode, video_data):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


@app.route('/api/add-category', methods=['POST'])
def api_add_category():
    """API endpoint to add a new category."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Missing category name'})
    
    categories_data = load_categories()
    
    if name in categories_data:
        return jsonify({'success': False, 'error': 'Category already exists'})
    
    # Add empty category
    categories_data[name] = {
        'size': 0,
        'videos': []
    }
    
    if save_categories(categories_data):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


@app.route('/api/rename-category', methods=['POST'])
def api_rename_category():
    """API endpoint to rename a category."""
    data = request.get_json()
    
    old_name = data.get('old_name', '').strip()
    new_name = data.get('new_name', '').strip()
    
    if not old_name or not new_name:
        return jsonify({'success': False, 'error': 'Missing category name'})
    
    if old_name == new_name:
        return jsonify({'success': True})
    
    categories_data = load_categories()
    
    if old_name not in categories_data:
        return jsonify({'success': False, 'error': 'Category not found'})
    
    if new_name in categories_data:
        return jsonify({'success': False, 'error': 'New category name already exists'})
    
    # Rename the category
    categories_data[new_name] = categories_data.pop(old_name)
    
    # Update all video category.json files that reference this category
    for video in categories_data[new_name].get('videos', []):
        shortcode = video.get('shortcode', '')
        if shortcode:
            video_data = load_video_category(shortcode)
            if video_data:
                if video_data.get('category') == old_name:
                    video_data['category'] = new_name
                if video_data.get('moved_to') == old_name:
                    video_data['moved_to'] = new_name
                if video_data.get('moved_from') == old_name:
                    video_data['moved_from'] = new_name
                if video_data.get('excluded_from') == old_name:
                    video_data['excluded_from'] = new_name
                save_video_category(shortcode, video_data)
    
    if save_categories(categories_data):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


@app.route('/api/delete-category', methods=['POST'])
def api_delete_category():
    """API endpoint to delete a category."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Missing category name'})
    
    categories_data = load_categories()
    
    if name not in categories_data:
        return jsonify({'success': False, 'error': 'Category not found'})
    
    # Clear category from all videos in this category
    for video in categories_data[name].get('videos', []):
        shortcode = video.get('shortcode', '')
        if shortcode:
            video_data = load_video_category(shortcode)
            if video_data:
                video_data['category'] = None
                video_data['excluded'] = True
                video_data['excluded_from'] = name
                save_video_category(shortcode, video_data)
    
    # Remove category
    del categories_data[name]
    
    if save_categories(categories_data):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


def find_video(shortcode: str) -> str | None:
    """Find the video file for a shortcode."""
    video_dir = Path(REEL_ARCHIVE_DIR) / shortcode
    
    if not video_dir.exists():
        return None
    
    # Look for mp4 files
    for pattern in [f"*{shortcode}*.mp4", "*.mp4"]:
        matches = list(video_dir.glob(pattern))
        if matches:
            return str(matches[0])
    
    return None


def load_transcript(shortcode: str) -> str | None:
    """Load transcript text for a video."""
    video_dir = Path(REEL_ARCHIVE_DIR) / shortcode
    
    if not video_dir.exists():
        return None
    
    # Look for txt files
    for pattern in [f"*{shortcode}*.txt", "*.txt"]:
        matches = list(video_dir.glob(pattern))
        if matches:
            try:
                with open(matches[0], 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
    
    return None


@app.route('/video/<shortcode>')
def serve_video(shortcode: str):
    """Serve the video file for preview."""
    video_path = find_video(shortcode)
    
    if video_path:
        directory = os.path.dirname(video_path)
        filename = os.path.basename(video_path)
        return send_from_directory(directory, filename)
    
    return '', 404


def main():
    parser = argparse.ArgumentParser(description='Category Review Web App')
    parser.add_argument(
        '--dir',
        type=str,
        default='~/reel_archive',
        help='Base directory containing reels (default: ~/reel_archive)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to run the server on (default: 5000)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    
    args = parser.parse_args()
    
    global REEL_ARCHIVE_DIR
    REEL_ARCHIVE_DIR = os.path.expanduser(args.dir)
    
    if not os.path.exists(REEL_ARCHIVE_DIR):
        print(f"❌ Directory not found: {REEL_ARCHIVE_DIR}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║               📁 Category Review Web App                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Archive: {REEL_ARCHIVE_DIR:<52} ║
║  URL:     http://{args.host}:{args.port:<45} ║
╠══════════════════════════════════════════════════════════════════╣
║  Keyboard Shortcuts:                                             ║
║    X        - Exclude selected video                             ║
║    U        - Undo exclusion/move                                ║
║    M        - Move to different category                         ║
║    Space    - Toggle selection (for bulk ops)                    ║
║    A        - Select all visible videos                          ║
║    P        - Preview video with transcript                      ║
║    ←/→      - Navigate between videos                            ║
║    Escape   - Close modal                                        ║
║                                                                  ║
║  Press Ctrl+C to stop the server                                 ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
