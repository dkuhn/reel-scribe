#!/usr/bin/env python3
"""
Categorize Instagram Reels based on transcripts, tags, and post descriptions.
Uses TF-IDF vectorization and K-means clustering to discover themes automatically.

NEW: Interactive mode - discovers potential topics and lets you choose which ones to use!

Usage:
    # Interactive mode (recommended) - discover topics and choose
    python cluster_reel_videos.py --dir ~/reel_archive --interactive
    
    # Auto mode - fully automatic clustering
    python cluster_reel_videos.py --dir ~/reel_archive
    
    # Use predefined categories
    python cluster_reel_videos.py --dir ~/reel_archive --categories "Triathlon,Comedy,Parenting,Cooking"
"""
# 1,2,3,4,5,6,7,8,8,10,12,13,15,16,19,22,25,24,21,+Christian,+Management,+Leadership
import os
import sys
import json
import argparse
import re
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import LatentDirichletAllocation


# Extended stop words for German and English
EXTENDED_STOP_WORDS = frozenset([
    # English stop words (common ones)
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
    'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
    'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'some', 'such',
    'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
    'now', 'then', 'here', 'there', 'also', 'well', 'back', 'even', 'still',
    'way', 'know', 'get', 'make', 'go', 'see', 'come', 'take', 'think', 'want',
    'really', 'like', 'yeah', 'yes', 'okay', 'oh', 'um', 'uh', 'gonna', 'wanna',
    'your', 'them', 'him', 'her', 'his', 'our', 'their', 'one', 'two', 'three',
    'got', 'going', 'said', 'say', 'tell', 'look', 'give', 'good', 'time',
    'never', 'ever', 'around', 'because', 'out', 'don', 'let', 'hey', 'hello',
    
    # Social media noise
    'follow', 'followme', 'followforfollow', 'like', 'likes', 'share', 'comment',
    'reels', 'reel', 'instagram', 'insta', 'tiktok', 'viral', 'fyp', 'foryou',
    'video', 'videos', 'music', 'song', 'credit', 'credits', 'via', 'tag',
    'dm', 'link', 'bio', 'page', 'check', 'watch', 'subscribe', 'youtube',
    
    # German stop words (sehr häufig)
    'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines',
    'und', 'oder', 'aber', 'in', 'zu', 'von', 'mit', 'nach', 'bei', 'aus',
    'auf', 'für', 'über', 'unter', 'durch', 'um', 'an', 'vor', 'zwischen',
    'ist', 'sind', 'war', 'waren', 'sein', 'werden', 'wurde', 'worden',
    'haben', 'hat', 'hatte', 'hatten', 'ich', 'du', 'er', 'sie', 'es',
    'wir', 'ihr', 'man', 'was', 'wer', 'wie', 'wo', 'wann', 'warum',
    'dieser', 'diese', 'dieses', 'jener', 'jene', 'jenes', 'welcher', 'welche',
    'nicht', 'kein', 'keine', 'keiner', 'nur', 'auch', 'noch', 'schon',
    'mehr', 'sehr', 'viel', 'so', 'da', 'hier', 'dort', 'dann', 'als',
    'wenn', 'ob', 'dass', 'weil', 'denn', 'ja', 'nein', 'doch', 'mal',
    'kann', 'muss', 'soll', 'will', 'mag', 'darf', 'konnte', 'musste',
    'sollte', 'wollte', 'machen', 'gehen', 'kommen', 'sehen', 'wissen',
    'halt', 'eben', 'etwa', 'irgendwie', 'eigentlich', 'gerade', 'einfach',
    'dir', 'mir', 'dich', 'mich', 'sich', 'jetzt', 'immer', 'alles', 'hast',
])


# Suggested topic keywords for common content themes (used for discovery hints)
TOPIC_KEYWORDS = {
    'Triathlon': ['triathlon', 'ironman', 'swim bike run', 'transition', 'tri training', 'wetsuit', 'aero', 't1', 't2', 'brick', '70.3', 'triathlete'],
    'Guitar': ['guitar', 'gitarre', 'acoustic', 'electric guitar', 'riff', 'chord', 'fretboard', 'strum', 'picking', 'guitarist', 'tabs', 'fender', 'gibson', 'amp'],
    'Bodybuilding': ['bodybuilding', 'bodybuilder', 'muscle', 'gains', 'bulk', 'cut', 'physique', 'competition', 'pose', 'mr olympia', 'shredded', 'biceps', 'triceps', 'legs', 'pump'],
    'Running': ['running', 'laufen', 'marathon', 'jogging', 'pace', 'tempo', 'kilometer', 'km', 'halbmarathon', 'run', 'läufer', 'joggen', 'strava', 'garmin', 'lauf'],
    'Swimming': ['schwimmen', 'swimming', 'pool', 'crawl', 'freestyle', 'breaststroke', 'lanes', 'swim', 'bahnen', 'kraulen', 'schwimmbad'],
    'Cycling': ['cycling', 'radfahren', 'bike', 'fahrrad', 'rennrad', 'peloton', 'watts', 'cadence', 'zwift', 'rad', 'velo'],
    'Fitness': ['fitness', 'workout', 'training', 'gym', 'exercise', 'muscle', 'strength', 'cardio', 'sport', 'fit', 'trainieren'],
    'Comedy': ['comedy', 'funny', 'lustig', 'witzig', 'humor', 'lachen', 'joke', 'witz', 'sketch', 'prank', 'satire', 'spaß'],
    'Stand-up': ['standup', 'stand-up', 'comedian', 'bühne', 'stage', 'publikum', 'audience', 'kabarett', 'comedy special', 'open mic'],
    'Parenting': ['eltern', 'parenting', 'kinder', 'kids', 'baby', 'familie', 'family', 'mama', 'papa', 'vater', 'mutter', 'kind', 'sohn', 'tochter', 'erziehung'],
    'Cooking': ['kochen', 'cooking', 'rezept', 'recipe', 'küche', 'kitchen', 'essen', 'food', 'meal', 'cook', 'chef', 'ingredients', 'zutaten', 'gericht'],
    'Travel': ['travel', 'reisen', 'urlaub', 'vacation', 'destination', 'hotel', 'flight', 'explore', 'reise', 'trip', 'airport', 'flug'],
    'Cats': ['katze', 'cat', 'kitten', 'meow', 'miau', 'feline', 'kitty', 'katzen', 'cats', 'kätzchen'],
    'Dogs': ['hund', 'dog', 'puppy', 'welpe', 'bark', 'bellen', 'canine', 'hunde', 'dogs', 'doggo'],
    'Pets': ['haustier', 'pet', 'animal', 'tier', 'cute', 'süß', 'tiere', 'animals'],
    'Work': ['arbeit', 'work', 'job', 'office', 'büro', 'career', 'meeting', 'colleague', 'kollege', 'beruf', 'chef', 'boss', 'arbeiten', 'firma', 'company'],
    'Relationships': ['beziehung', 'relationship', 'partner', 'liebe', 'love', 'dating', 'marriage', 'ehe', 'freund', 'freundin', 'boyfriend', 'girlfriend', 'couple', 'paar'],
    'Tech': ['tech', 'technology', 'programming', 'code', 'software', 'app', 'computer', 'digital', 'iphone', 'android', 'developer'],
    'Music': ['musik', 'music', 'song', 'singing', 'guitar', 'piano', 'band', 'concert', 'singen', 'konzert', 'musiker'],
    'Dance': ['tanz', 'dance', 'dancing', 'choreography', 'moves', 'tanzen', 'dancer', 'tänzer'],
    'Fashion': ['fashion', 'mode', 'style', 'outfit', 'clothing', 'kleidung', 'trend', 'wear', 'clothes', 'look'],
    'Beauty': ['beauty', 'makeup', 'skincare', 'cosmetic', 'schönheit', 'pflege', 'skin', 'hair', 'haare'],
    'Health': ['gesundheit', 'health', 'wellness', 'mental health', 'meditation', 'yoga', 'healthy', 'gesund', 'therapie'],
    'Education': ['education', 'lernen', 'learning', 'schule', 'school', 'studium', 'university', 'uni', 'student', 'studieren', 'lehrer', 'teacher'],
    'Gaming': ['gaming', 'gamer', 'videospiele', 'games', 'playstation', 'xbox', 'nintendo', 'stream', 'twitch', 'spielen'],
    'Nature': ['natur', 'nature', 'outdoor', 'hiking', 'wandern', 'forest', 'wald', 'berg', 'mountain', 'see', 'lake'],
    'DIY': ['diy', 'selbermachen', 'handwerk', 'craft', 'basteln', 'project', 'howto', 'tutorial', 'hack', 'lifehack'],
    'Motivation': ['motivation', 'inspiration', 'mindset', 'success', 'goals', 'ziele', 'erfolg', 'motiviert', 'inspire'],
    'German Comedy': ['deutsch', 'german', 'deutschland', 'österreich', 'schweiz', 'comedy', 'lustig', 'witzig', 'humor'],
    'Sports': ['sport', 'sports', 'athlete', 'team', 'game', 'match', 'spiel', 'spieler', 'football', 'basketball'],
    'Science': ['science', 'wissenschaft', 'research', 'experiment', 'physics', 'chemistry', 'biology', 'scientist'],
    'Art': ['art', 'kunst', 'painting', 'drawing', 'artist', 'künstler', 'creative', 'kreativ', 'design'],

    # Additional categories
    'Christian': ['christian', 'jesus', 'god', 'bible', 'church', 'faith', 'prayer', 'gott', 'kirche', 'glaube', 'gebet', 'blessed', 'gospel'],
    'Management': ['management', 'manager', 'team', 'führung', 'projekt', 'project', 'strategy', 'strategie', 'business', 'organization'],
    'Leadership': ['leadership', 'leader', 'führung', 'leiten', 'ceo', 'executive', 'vision', 'inspire', 'team lead', 'mentor'],
    'Entrepreneurship': ['entrepreneur', 'startup', 'gründer', 'founder', 'business', 'unternehmer', 'venture', 'hustle', 'side hustle'],
    'Finance': ['finance', 'money', 'geld', 'investing', 'investment', 'stocks', 'aktien', 'crypto', 'bitcoin', 'budget', 'savings', 'wealth'],
    'Marketing': ['marketing', 'brand', 'social media', 'content', 'advertising', 'werbung', 'campaign', 'growth', 'audience'],
    'Productivity': ['productivity', 'produktivität', 'efficiency', 'time management', 'focus', 'habits', 'routine', 'morning routine'],
    'Psychology': ['psychology', 'psychologie', 'mind', 'brain', 'behavior', 'mental', 'cognitive', 'therapy', 'anxiety', 'depression'],
    'Self-Improvement': ['self improvement', 'personal development', 'growth', 'selbstverbesserung', 'habits', 'discipline', 'better', 'change'],
    'Meditation': ['meditation', 'mindfulness', 'achtsamkeit', 'breathing', 'calm', 'peace', 'zen', 'relaxation', 'stress relief'],
    'Yoga': ['yoga', 'asana', 'stretching', 'flexibility', 'vinyasa', 'namaste', 'breathwork', 'flow'],
    'Nutrition': ['nutrition', 'ernährung', 'diet', 'diät', 'calories', 'protein', 'healthy eating', 'macro', 'vegan', 'vegetarian'],
    'Weight Loss': ['weight loss', 'abnehmen', 'fat loss', 'diet', 'calories', 'metabolism', 'keto', 'fasting', 'intermittent'],
    'Cars': ['car', 'auto', 'vehicle', 'driving', 'fahren', 'autos', 'automobile', 'motor', 'bmw', 'mercedes', 'tesla'],
    'Photography': ['photography', 'fotografie', 'photo', 'camera', 'kamera', 'shooting', 'portrait', 'landscape', 'lightroom'],
    'Film': ['film', 'movie', 'cinema', 'kino', 'director', 'actor', 'scene', 'netflix', 'hollywood', 'streaming'],
    'Books': ['book', 'buch', 'reading', 'lesen', 'author', 'novel', 'literature', 'kindle', 'audiobook', 'bestseller'],
    'Real Estate': ['real estate', 'immobilien', 'property', 'house', 'haus', 'apartment', 'wohnung', 'rent', 'mortgage', 'investing'],
    'Gardening': ['garden', 'garten', 'plants', 'pflanzen', 'growing', 'flowers', 'blumen', 'soil', 'seeds', 'harvest'],
    'Home Decor': ['home decor', 'interior', 'einrichtung', 'furniture', 'möbel', 'decoration', 'living room', 'design', 'ikea'],
    'Chess': ['chess', 'schach', 'checkmate', 'opening', 'endgame', 'grandmaster', 'knight', 'bishop', 'queen', 'pawn'],
    'History': ['history', 'geschichte', 'historical', 'ancient', 'war', 'krieg', 'century', 'civilization', 'empire'],
    'Politics': ['politics', 'politik', 'government', 'election', 'wahl', 'democracy', 'policy', 'politician', 'vote'],
    'News': ['news', 'nachrichten', 'current events', 'breaking', 'update', 'report', 'headline', 'journalist'],
    'Spirituality': ['spiritual', 'spirituell', 'soul', 'seele', 'universe', 'energy', 'awakening', 'consciousness', 'manifest'],
    'Minimalism': ['minimalism', 'minimalismus', 'declutter', 'simple', 'less is more', 'organize', 'tidy', 'essentials'],
    'Wee': ['wee', 'fail'],
    'Mathematik': ['math', 'maths', 'algebra', 'geometry', 'calculus', 'statistics', 'numbers', 'formula', 'logic', 'equations', 'mathe', 'rechnen', 'zahlen', 'stochastik', 'analysis'],
    'Fußball': ['fußball', 'football', 'soccer', 'goal', 'tor', 'stadium', 'stadion', 'match', 'bundesliga', 'ball', 'champions league', 'fifa', 'kick', 'team', 'wm', 'em', 'soccergame', 'kicker', 'elfmeter', 'abseits'],
    'Fighting': ['fighting', 'fight', 'kampf', 'kampfsport', 'mma', 'boxing', 'boxen', 'kickboxing', 'martial arts', 'ufc', 'knockout', 'ko', 'sparring', 'training', 'ring', 'cage', 'gloves', 'warrior'],
    'Marriage': ['marriage', 'ehe', 'wedding', 'hochzeit', 'bride', 'braut', 'groom', 'bräutigam', 'husband', 'wife', 'ehemann', 'ehefrau', 'married', ',verheiratet', 'anniversary', 'jahrestag', 'proposal', 'verlobung', 'vows', 'love', 'liebe']

}

def suggest_additional_categories(selected_topics, videos_data, num_suggestions=20):
    """
    Suggest additional categories based on selected topics and video content.
    
    Analyzes the video corpus for themes not covered by selected topics,
    using TF-IDF to find distinguishing terms.
    
    Args:
        selected_topics: List of already selected topic names
        videos_data: List of text documents from videos
        num_suggestions: Number of suggestions to return
    
    Returns:
        list: List of (suggested_topic, matching_count) tuples
    """
    print(f"\n{'='*70}")
    print("🔍 ANALYZING CONTENT FOR ADDITIONAL CATEGORIES")
    print(f"{'='*70}\n")
    
    # Get keywords from already selected topics
    selected_keywords = set()
    for topic in selected_topics:
        if topic in TOPIC_KEYWORDS:
            selected_keywords.update(k.lower() for k in TOPIC_KEYWORDS[topic])
    
    print(f"  📋 Already selected: {len(selected_topics)} categories")
    print(f"  🔑 Keywords covered: {len(selected_keywords)}")
    
    # Find unselected topics that have matches in the corpus
    suggestions = []
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        if topic in selected_topics:
            continue
        
        # Count how many videos match this topic's keywords
        topic_keywords_lower = [k.lower() for k in keywords]
        matching_videos = 0
        
        for text in videos_data:
            text_lower = text.lower()
            for kw in topic_keywords_lower:
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    matching_videos += 1
                    break
        
        if matching_videos > 0:
            # Don't suggest if keywords overlap too much with selected
            keyword_overlap = len(set(topic_keywords_lower) & selected_keywords)
            overlap_ratio = keyword_overlap / len(topic_keywords_lower) if topic_keywords_lower else 0
            
            if overlap_ratio < 0.5:  # Less than 50% overlap
                suggestions.append((topic, matching_videos, overlap_ratio))
    
    # Sort by matching videos (descending)
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n  💡 Found {len(suggestions)} potential additional categories:\n")
    
    for i, (topic, count, overlap) in enumerate(suggestions[:num_suggestions], 1):
        overlap_str = f" ({overlap*100:.0f}% overlap)" if overlap > 0.1 else ""
        print(f"     {i:2}. {topic}: {count} videos{overlap_str}")
    
    if len(suggestions) > num_suggestions:
        print(f"\n     ... and {len(suggestions) - num_suggestions} more")
    
    return suggestions[:num_suggestions]


def load_manual_categories(base_dir):
    """
    Load all manually categorized videos from category.json files.
    
    Scans the base directory for videos with manual:true in their category.json.
    
    Args:
        base_dir: Base directory containing video subdirectories
    
    Returns:
        dict: {category: [shortcodes]} mapping
    """
    base_dir = os.path.expanduser(base_dir)
    manual_categories = defaultdict(list)
    
    subdirs = [d for d in os.listdir(base_dir) 
               if os.path.isdir(os.path.join(base_dir, d)) and d != 'whisper']
    
    for shortcode in subdirs:
        category_file = os.path.join(base_dir, shortcode, 'category.json')
        
        if os.path.exists(category_file):
            try:
                with open(category_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('manual', False):
                        category = data.get('category', 'Unknown')
                        manual_categories[category].append(shortcode)
            except (json.JSONDecodeError, IOError):
                pass
    
    return dict(manual_categories)


def learn_from_manual_categories(base_dir, videos_data, shortcodes, metadata):
    """
    Extract distinctive keywords from manually categorized videos using TF-IDF.
    
    For each category with manual entries, identifies the keywords that
    distinguish those videos from others.
    
    Args:
        base_dir: Base directory
        videos_data: List of text documents
        shortcodes: List of shortcodes
        metadata: Dict with video metadata
    
    Returns:
        dict: {category: [learned_keywords]} mapping
    """
    manual_categories = load_manual_categories(base_dir)
    
    if not manual_categories:
        return {}
    
    # Create index for quick lookup
    shortcode_to_idx = {sc: i for i, sc in enumerate(shortcodes)}
    
    learned_keywords = {}
    
    for category, manual_shortcodes in manual_categories.items():
        # Get indices of manually categorized videos
        indices = [shortcode_to_idx[sc] for sc in manual_shortcodes if sc in shortcode_to_idx]
        
        if len(indices) < 2:
            continue  # Need at least 2 examples to learn
        
        # Get text of manual videos
        manual_texts = [videos_data[i] for i in indices]
        
        # Get text of other videos (sample to keep it fast)
        other_indices = [i for i in range(len(videos_data)) if i not in indices]
        sample_size = min(500, len(other_indices))
        if sample_size > 0:
            np.random.seed(42)
            sample_indices = np.random.choice(other_indices, sample_size, replace=False)
            other_texts = [videos_data[i] for i in sample_indices]
        else:
            other_texts = []
        
        if not other_texts:
            continue
        
        # Use TF-IDF to find distinctive terms
        all_texts = manual_texts + other_texts
        labels = [1] * len(manual_texts) + [0] * len(other_texts)
        
        try:
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=list(EXTENDED_STOP_WORDS),
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.9
            )
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF for manual vs other
            manual_avg = np.array(tfidf_matrix[:len(manual_texts)].mean(axis=0)).flatten()
            other_avg = np.array(tfidf_matrix[len(manual_texts):].mean(axis=0)).flatten()
            
            # Find terms that are more distinctive in manual videos
            # Use ratio: (manual_avg + 0.001) / (other_avg + 0.001)
            distinctiveness = (manual_avg + 0.001) / (other_avg + 0.001)
            
            # Get top distinctive terms that appear often in manual
            top_indices = []
            for idx in np.argsort(distinctiveness)[::-1]:
                if manual_avg[idx] > 0.01:  # Must appear in manual videos
                    top_indices.append(idx)
                    if len(top_indices) >= 15:
                        break
            
            distinctive_terms = [feature_names[i] for i in top_indices]
            
            # Filter out terms that are already in predefined keywords
            existing_keywords = set()
            if category in TOPIC_KEYWORDS:
                existing_keywords = set(k.lower() for k in TOPIC_KEYWORDS[category])
            
            new_terms = [t for t in distinctive_terms if t.lower() not in existing_keywords][:10]
            
            if new_terms:
                learned_keywords[category] = new_terms
        
        except Exception as e:
            print(f"  ⚠️  Error learning from {category}: {e}")
            continue
    
    return learned_keywords


def fine_tune_classification(base_dir, videos_data, shortcodes, metadata, selected_topics):
    """
    Show what has been learned from manual categorizations.
    
    Displays the manual categories found and the distinctive keywords
    that have been extracted from them.
    
    Args:
        base_dir: Base directory
        videos_data: List of text documents
        shortcodes: List of shortcodes
        metadata: Dict with video metadata
        selected_topics: List of selected topics (unused, for API compatibility)
    
    Returns:
        dict: Learned keywords mapping
    """
    print(f"\n{'='*70}")
    print("🎓 LEARNING FROM MANUAL CATEGORIZATIONS")
    print(f"{'='*70}\n")
    
    manual_categories = load_manual_categories(base_dir)
    
    if not manual_categories:
        print("  ⚠️  No manual categorizations found.")
        print("  To create manual entries, edit category.json files and set 'manual': true")
        return {}
    
    total_manual = sum(len(v) for v in manual_categories.values())
    print(f"  📚 Found {total_manual} manually categorized videos in {len(manual_categories)} categories:\n")
    
    for category, scs in sorted(manual_categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"     • {category}: {len(scs)} videos")
    
    # Learn keywords
    print(f"\n  🔍 Extracting distinctive keywords...")
    learned = learn_from_manual_categories(base_dir, videos_data, shortcodes, metadata)
    
    if learned:
        print(f"\n  📝 Learned keywords for {len(learned)} categories:\n")
        for category, keywords in learned.items():
            kw_str = ", ".join(keywords[:8])
            if len(keywords) > 8:
                kw_str += f", ... (+{len(keywords)-8} more)"
            print(f"     • {category}: {kw_str}")
    else:
        print("\n  ⚠️  Could not extract distinctive keywords (need at least 2 examples per category)")
    
    return learned


def classify_with_fine_tuning(videos_data, shortcodes, metadata, selected_topics, base_dir, learned_keywords):
    """
    Classify videos using both predefined and learned keywords.
    
    Learned keywords receive 2x weight in scoring to prioritize
    patterns discovered from manual categorizations.
    
    Args:
        videos_data: List of text documents
        shortcodes: List of shortcodes
        metadata: Dict with video metadata
        selected_topics: List of topic names
        base_dir: Base directory
        learned_keywords: Dict of learned keywords from manual categories
    
    Returns:
        dict: Category assignments
    """
    print(f"\n{'='*70}")
    print(f"🎯 CLASSIFYING WITH FINE-TUNED MODEL")
    print(f"{'='*70}\n")
    
    base_dir = os.path.expanduser(base_dir)
    
    # Build keyword sets combining predefined and learned
    topic_keywords = {}
    
    # Add predefined keywords
    for topic in selected_topics:
        if topic in TOPIC_KEYWORDS:
            topic_keywords[topic] = [k.lower() for k in TOPIC_KEYWORDS[topic]]
        else:
            words = re.findall(r'\b[a-zA-ZäöüßÄÖÜ]{3,}\b', topic.lower())
            topic_keywords[topic] = words
    
    # Add/extend with learned keywords (higher weight)
    for category, keywords in learned_keywords.items():
        if category in topic_keywords:
            # Extend existing - learned keywords get priority
            existing = set(topic_keywords[category])
            for kw in keywords:
                if kw.lower() not in existing:
                    topic_keywords[category].insert(0, kw.lower())  # Add at front for priority
        else:
            # New category from manual entries
            topic_keywords[category] = [k.lower() for k in keywords]
    
    # Classify videos
    categories = defaultdict(list)
    unclassified = []
    manual_kept = 0
    auto_classified = 0
    improved_by_learning = 0
    
    for idx, (text, shortcode) in enumerate(zip(videos_data, shortcodes)):
        video_dir = os.path.join(base_dir, shortcode)
        category_file = os.path.join(video_dir, 'category.json')
        
        # Check for manual category
        existing_category = None
        if os.path.exists(category_file):
            try:
                with open(category_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if existing_data.get('manual', False):
                        existing_category = existing_data.get('category')
                        manual_kept += 1
            except (json.JSONDecodeError, IOError):
                pass
        
        if existing_category:
            categories[existing_category].append({
                'shortcode': shortcode,
                'score': 999,
                'matched_keywords': ['manual'],
                'metadata': metadata.get(shortcode, {}),
                'manual': True
            })
            continue
        
        text_lower = text.lower()
        
        # Score each topic
        topic_scores = []
        for topic, keywords in topic_keywords.items():
            score = 0
            matched = []
            
            # Check if this topic has learned keywords
            has_learned = topic in learned_keywords
            
            for i, keyword in enumerate(keywords):
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Learned keywords (at front of list) get 2x weight
                    weight = 2 if (has_learned and i < len(learned_keywords.get(topic, []))) else 1
                    score += len(keyword) * len(matches) * weight
                    matched.append(keyword)
            
            if score > 0:
                topic_scores.append((topic, score, matched, has_learned))
        
        if topic_scores:
            topic_scores.sort(key=lambda x: x[1], reverse=True)
            best_topic, score, matched, used_learned = topic_scores[0]
            
            if used_learned:
                improved_by_learning += 1
            
            categories[best_topic].append({
                'shortcode': shortcode,
                'score': score,
                'matched_keywords': matched[:5],
                'metadata': metadata.get(shortcode, {}),
                'manual': False
            })
            auto_classified += 1
            
            _save_video_category(video_dir, shortcode, best_topic, score, matched[:5], False)
        else:
            unclassified.append(shortcode)
            _save_video_category(video_dir, shortcode, 'Other / Uncategorized', 0, [], False)
    
    # Add uncategorized
    if unclassified:
        categories['Other / Uncategorized'] = [
            {'shortcode': sc, 'score': 0, 'matched_keywords': [], 'metadata': metadata.get(sc, {}), 'manual': False}
            for sc in unclassified
        ]
    
    # Print results
    print(f"Classification complete!\n")
    print(f"  📊 Auto-classified: {auto_classified} videos")
    print(f"  ✋ Manual preserved: {manual_kept} videos")
    print(f"  🎓 Improved by learning: {improved_by_learning} videos")
    print()
    
    sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    
    for topic, videos in sorted_cats:
        manual_count = sum(1 for v in videos if v.get('manual', False))
        learned_marker = " 🎓" if topic in learned_keywords else ""
        manual_str = f" ({manual_count} manual)" if manual_count > 0 else ""
        print(f"  📁 {topic}: {len(videos)} videos{manual_str}{learned_marker}")
    
    if unclassified:
        print(f"\n  ⚠️  {len(unclassified)} videos couldn't be classified")
    
    # Save results
    output_file = os.path.join(base_dir, 'categories.json')
    
    export_data = {}
    for topic, videos in categories.items():
        export_data[topic] = {
            'size': len(videos),
            'learned_keywords': learned_keywords.get(topic, [])[:10],
            'videos': [
                {
                    'shortcode': v['shortcode'],
                    'score': v['score'],
                    'url': f"https://www.instagram.com/reel/{v['shortcode']}",
                    'matched_keywords': v['matched_keywords'],
                    'manual': v.get('manual', False)
                }
                for v in sorted(videos, key=lambda x: x['score'], reverse=True)
            ]
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    return categories


def create_readable_category_name(terms, min_words=2, max_words=3):
    """
    Create a readable category name from top terms by filtering common words
    and finding meaningful multi-word phrases.
    
    Args:
        terms: List of top terms for the cluster
        min_words: Minimum words in the name
        max_words: Maximum words in the name
    
    Returns:
        str: Readable category name
    """
    # Filter out very short terms and stop words
    meaningful_terms = []
    for term in terms:
        words = term.split()
        # Keep if it's a multi-word phrase or a meaningful single word (>3 chars)
        if len(words) > 1 or (len(term) > 3 and term.lower() not in EXTENDED_STOP_WORDS):
            meaningful_terms.append(term)
            if len(meaningful_terms) >= max_words * 2:  # Get extras for selection
                break
    
    # Prefer longer phrases first, then single meaningful words
    phrases = [t for t in meaningful_terms if len(t.split()) > 1]
    words = [t for t in meaningful_terms if len(t.split()) == 1]
    
    # Build category name
    selected = []
    
    # Start with best phrase if available
    if phrases and len(selected) < max_words:
        selected.append(phrases[0])
    
    # Add more phrases or words
    for term in phrases[1:] + words:
        if len(selected) >= max_words:
            break
        # Avoid redundancy
        if not any(term.lower() in s.lower() or s.lower() in term.lower() for s in selected):
            selected.append(term)
    
    # Ensure minimum words
    while len(selected) < min_words and len(meaningful_terms) > len(selected):
        for term in meaningful_terms:
            if term not in selected:
                selected.append(term)
                break
    
    if not selected:
        selected = terms[:max_words]
    
    return " / ".join(selected[:max_words])


def collect_video_data(base_dir):
    """
    Collect all transcripts, tags, and post descriptions from processed videos.
    
    Args:
        base_dir (str): Base directory containing reel subdirectories.
    
    Returns:
        tuple: (videos_data, shortcodes, metadata) where:
            - videos_data: list of combined text from each video
            - shortcodes: list of shortcodes corresponding to each video
            - metadata: dict with detailed info for each shortcode
    """
    base_dir = os.path.expanduser(base_dir)
    
    if not os.path.exists(base_dir):
        print(f"❌ Directory does not exist: {base_dir}")
        return [], [], {}
    
    print(f"\n{'='*70}")
    print(f"📂 Scanning videos in: {base_dir}")
    print(f"{'='*70}\n")
    
    videos_data = []
    shortcodes = []
    metadata = {}
    
    subdirs = [d for d in os.listdir(base_dir) 
               if os.path.isdir(os.path.join(base_dir, d)) and d != 'whisper']
    
    for shortcode in subdirs:
        subdir = os.path.join(base_dir, shortcode)
        
        # Read whisper transcript
        whisper_dir = os.path.join(subdir, 'whisper')
        transcript_text = ""
        if os.path.exists(whisper_dir):
            txt_files = [f for f in os.listdir(whisper_dir) if f.endswith('.txt')]
            if txt_files:
                try:
                    with open(os.path.join(whisper_dir, txt_files[0]), 'r', encoding='utf-8') as f:
                        transcript_text = f.read().strip()
                except Exception as e:
                    pass
        
        # Read tags
        tags_text = ""
        tags_list = []
        tags_file = os.path.join(subdir, f"{shortcode}.tags.txt")
        if os.path.exists(tags_file):
            try:
                with open(tags_file, 'r', encoding='utf-8') as f:
                    tags_text = f.read().strip()
                    tags_list = [t.strip() for t in tags_text.split('\n') if t.strip()]
            except Exception as e:
                pass
        
        # Read Instagram post description
        post_text = ""
        post_files = [f for f in os.listdir(subdir) if f.endswith('.txt') and 'UTC_' in f]
        if post_files:
            try:
                with open(os.path.join(subdir, post_files[0]), 'r', encoding='utf-8') as f:
                    post_text = f.read().strip()
            except Exception as e:
                pass
        
        # Only include videos with some text content
        if transcript_text or tags_text or post_text:
            # Combine all text sources with different weights
            # Tags: 5x (if present), Post description: 3x, Transcript: 3x (equally important)
            if tags_text:
                combined_text = f"{tags_text} {tags_text} {tags_text} {tags_text} {tags_text} {post_text} {post_text} {post_text} {transcript_text} {transcript_text} {transcript_text}"
            else:
                # No tags - weight both post description and transcript heavily
                combined_text = f"{post_text} {post_text} {post_text} {transcript_text} {transcript_text} {transcript_text}"
            
            videos_data.append(combined_text)
            shortcodes.append(shortcode)
            metadata[shortcode] = {
                'transcript': transcript_text[:200] if transcript_text else "",
                'full_transcript': transcript_text,  # Store full transcript for keyword matching
                'tags': tags_list,
                'post_excerpt': post_text[:200] if post_text else "",
                'full_post': post_text,  # Store full post for keyword matching
                'has_transcript': bool(transcript_text),
                'has_tags': bool(tags_text),
                'has_post': bool(post_text)
            }
    
    print(f"✓ Found {len(videos_data)} videos with text content")
    print(f"  - With transcripts: {sum(1 for m in metadata.values() if m['has_transcript'])}")
    print(f"  - With tags: {sum(1 for m in metadata.values() if m['has_tags'])}")
    print(f"  - With post descriptions: {sum(1 for m in metadata.values() if m['has_post'])}")
    
    return videos_data, shortcodes, metadata


def discover_topics_lda(videos_data, n_topics=20):
    """
    Use Latent Dirichlet Allocation to discover topics in the corpus.
    
    Args:
        videos_data: List of text documents
        n_topics: Number of topics to discover
    
    Returns:
        list: List of (topic_name, keywords, estimated_count) tuples
    """
    # Use CountVectorizer for LDA
    count_vectorizer = CountVectorizer(
        max_features=500,
        min_df=2,
        max_df=0.8,
        stop_words=list(EXTENDED_STOP_WORDS),
        token_pattern=r'\b[a-zA-ZäöüßÄÖÜ]{3,}\b',
    )
    
    count_matrix = count_vectorizer.fit_transform(videos_data)
    feature_names = count_vectorizer.get_feature_names_out()
    
    # Fit LDA model
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
        learning_method='online'
    )
    lda.fit(count_matrix)
    
    # Extract topics
    topics = []
    doc_topics = lda.transform(count_matrix)
    
    for topic_idx, topic in enumerate(lda.components_):
        top_word_indices = topic.argsort()[-8:][::-1]
        keywords = [feature_names[i] for i in top_word_indices]
        
        # Count documents primarily in this topic
        primary_count = sum(1 for doc in doc_topics if doc.argmax() == topic_idx)
        
        if primary_count >= 2:  # Only include topics with at least 2 videos
            # Create a readable name from top keywords
            name_words = [w for w in keywords[:3] if len(w) > 3]
            topic_name = " / ".join(name_words) if name_words else keywords[0]
            topics.append((topic_name.title(), keywords, primary_count))
    
    return sorted(topics, key=lambda x: x[2], reverse=True)


def discover_topics_from_keywords(videos_data):
    """
    Match predefined topic keywords against the corpus to find relevant topics.
    
    Args:
        videos_data: List of text documents
    
    Returns:
        list: List of (topic_name, matched_keywords, count) tuples
    """
    all_text = " ".join(videos_data).lower()
    
    matched_topics = []
    for topic_name, keywords in TOPIC_KEYWORDS.items():
        matches = []
        count = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            occurrences = all_text.count(keyword_lower)
            if occurrences > 0:
                matches.append(keyword)
                count += occurrences
        
        if matches:
            # Estimate video count (rough: assume each keyword mention could be a different video)
            estimated_videos = min(count // 2, len(videos_data) // 3)
            if estimated_videos >= 1:
                matched_topics.append((topic_name, matches, estimated_videos))
    
    return sorted(matched_topics, key=lambda x: x[2], reverse=True)


def discover_topics_tfidf_clusters(videos_data, n_clusters=15):
    """
    Use TF-IDF + K-means to discover natural clusters and extract their themes.
    
    Args:
        videos_data: List of text documents
        n_clusters: Number of clusters to try
    
    Returns:
        list: List of (topic_name, keywords, count) tuples
    """
    vectorizer = TfidfVectorizer(
        max_features=400,
        min_df=2,
        max_df=0.7,
        ngram_range=(1, 3),
        stop_words=list(EXTENDED_STOP_WORDS),
        token_pattern=r'\b[a-zA-ZäöüßÄÖÜ]{3,}\b',
    )
    
    tfidf_matrix = vectorizer.fit_transform(videos_data)
    feature_names = vectorizer.get_feature_names_out()
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(tfidf_matrix)
    
    topics = []
    for cluster_id in range(n_clusters):
        cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
        
        if len(cluster_indices) >= 2:
            # Get top terms
            cluster_center = kmeans.cluster_centers_[cluster_id]
            top_indices = cluster_center.argsort()[-10:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            # Create name from meaningful terms
            name_words = [w for w in keywords[:4] if len(w) > 3 and w.lower() not in EXTENDED_STOP_WORDS]
            topic_name = " / ".join(name_words[:3]) if name_words else keywords[0]
            
            topics.append((topic_name.title(), keywords, len(cluster_indices)))
    
    return sorted(topics, key=lambda x: x[2], reverse=True)


def merge_similar_topics(all_topics, similarity_threshold=0.5):
    """
    Merge topics that have similar keywords.
    
    Args:
        all_topics: List of (name, keywords, count) tuples from various sources
        similarity_threshold: Jaccard similarity threshold for merging
    
    Returns:
        list: Deduplicated and merged topics
    """
    if not all_topics:
        return []
    
    # Group by similarity
    merged = []
    used = set()
    
    for i, (name1, keywords1, count1) in enumerate(all_topics):
        if i in used:
            continue
        
        # Find similar topics
        similar_counts = [count1]
        all_keywords = set(k.lower() for k in keywords1)
        best_name = name1
        
        for j, (name2, keywords2, count2) in enumerate(all_topics):
            if j <= i or j in used:
                continue
            
            kw1_set = set(k.lower() for k in keywords1)
            kw2_set = set(k.lower() for k in keywords2)
            
            # Jaccard similarity
            intersection = len(kw1_set & kw2_set)
            union = len(kw1_set | kw2_set)
            similarity = intersection / union if union > 0 else 0
            
            if similarity >= similarity_threshold:
                used.add(j)
                similar_counts.append(count2)
                all_keywords.update(kw2_set)
                # Keep the shorter, cleaner name
                if len(name2) < len(best_name) and '/' not in name2:
                    best_name = name2
        
        merged.append((best_name, list(all_keywords)[:10], max(similar_counts)))
        used.add(i)
    
    return sorted(merged, key=lambda x: x[2], reverse=True)


def discover_all_topics(videos_data, verbose=True):
    """
    Run multiple topic discovery methods and combine results.
    
    Args:
        videos_data: List of text documents
        verbose: Whether to print progress
    
    Returns:
        list: Combined and deduplicated topics
    """
    if verbose:
        print(f"\n{'='*70}")
        print("🔍 DISCOVERING TOPICS IN YOUR VIDEOS")
        print(f"{'='*70}\n")
    
    all_topics = []
    
    # Method 1: Predefined keyword matching
    if verbose:
        print("📌 Method 1: Matching against known topic categories...")
    keyword_topics = discover_topics_from_keywords(videos_data)
    if verbose:
        print(f"   Found {len(keyword_topics)} matching topics")
    all_topics.extend(keyword_topics)
    
    # Method 2: LDA topic modeling
    if verbose:
        print("📌 Method 2: LDA topic modeling...")
    try:
        lda_topics = discover_topics_lda(videos_data, n_topics=15)
        if verbose:
            print(f"   Discovered {len(lda_topics)} topics")
        all_topics.extend(lda_topics)
    except Exception as e:
        if verbose:
            print(f"   LDA failed: {e}")
    
    # Method 3: TF-IDF clustering
    if verbose:
        print("📌 Method 3: TF-IDF clustering...")
    cluster_topics = discover_topics_tfidf_clusters(videos_data, n_clusters=12)
    if verbose:
        print(f"   Found {len(cluster_topics)} cluster themes")
    all_topics.extend(cluster_topics)
    
    # Merge similar topics
    if verbose:
        print("\n🔄 Merging similar topics...")
    merged_topics = merge_similar_topics(all_topics, similarity_threshold=0.3)
    
    if verbose:
        print(f"✓ Final: {len(merged_topics)} unique topics discovered\n")
    
    return merged_topics


def interactive_topic_selection(discovered_topics, videos_data):
    """
    Present discovered topics to user and let them select which to use.
    
    Args:
        discovered_topics: List of (name, keywords, count) tuples
        videos_data: List of text documents (for custom topic validation)
    
    Returns:
        list: Selected topic names
    """
    print(f"\n{'='*70}")
    print("📋 DISCOVERED TOPICS")
    print(f"{'='*70}")
    print("\nHere are the topics I found in your videos:\n")
    
    # Show top 25 topics
    display_topics = discovered_topics[:25]
    
    for i, (name, keywords, count) in enumerate(display_topics, 1):
        keywords_str = ", ".join(keywords[:5])
        print(f"  {i:2d}. {name:<25} (~{count:3d} videos)  [{keywords_str}]")
    
    print(f"\n{'─'*70}")
    print("\n📝 HOW TO SELECT TOPICS:\n")
    print("  • Enter numbers separated by commas: 1,3,5,7")
    print("  • Enter 'all' to use all discovered topics")
    print("  • Enter 'top N' to use top N topics (e.g., 'top 10')")
    print("  • Add custom topics with '+': 1,3,5,+Triathlon,+German Comedy")
    print("  • Press Enter for smart auto-selection (top topics by coverage)")
    print()
    
    # Check if we're in an interactive terminal
    import sys
    if not sys.stdin.isatty():
        print("⚠️  Non-interactive mode detected (e.g., conda run)")
        print("   Using auto-selection. For interactive mode, run directly:")
        print("   python cluster_reel_videos.py --interactive")
        print()
        # Auto-select top topics
        selected = []
        covered = 0
        target = len(videos_data) * 0.7
        for name, keywords, count in discovered_topics:
            if covered < target or len(selected) < 5:
                selected.append(name)
                covered += count
            if len(selected) >= 12:
                break
        print(f"✓ Auto-selected {len(selected)} topics: {', '.join(selected)}")
        return selected
    
    while True:
        try:
            selection = input("Your selection: ").strip()
            
            if not selection:
                # Auto-select: take topics that cover at least 70% of videos
                selected = []
                covered = 0
                target = len(videos_data) * 0.7
                for name, keywords, count in discovered_topics:
                    if covered < target or len(selected) < 5:
                        selected.append(name)
                        covered += count
                    if len(selected) >= 12:
                        break
                print(f"\n✓ Auto-selected {len(selected)} topics: {', '.join(selected)}")
                return selected
            
            if selection.lower() == 'all':
                return [t[0] for t in display_topics]
            
            if selection.lower().startswith('top '):
                try:
                    n = int(selection.split()[1])
                    return [t[0] for t in display_topics[:n]]
                except (ValueError, IndexError):
                    print("❌ Invalid format. Use 'top N' where N is a number.")
                    continue
            
            # Parse selection
            selected = []
            parts = [p.strip() for p in selection.split(',')]
            
            for part in parts:
                if part.startswith('+'):
                    # Custom topic
                    custom = part[1:].strip()
                    if custom:
                        selected.append(custom)
                        print(f"   + Added custom topic: {custom}")
                else:
                    try:
                        idx = int(part) - 1
                        if 0 <= idx < len(display_topics):
                            selected.append(display_topics[idx][0])
                        else:
                            print(f"   ⚠️  Invalid number: {part}")
                    except ValueError:
                        # Might be a topic name directly
                        if part:
                            selected.append(part)
            
            if selected:
                print(f"\n✓ Selected {len(selected)} topics: {', '.join(selected)}")
                return selected
            else:
                print("❌ No valid selection. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user.")
            sys.exit(0)


def classify_videos_by_topics(videos_data, shortcodes, metadata, selected_topics, base_dir):
    """
    Classify videos into the selected topics using keyword matching and similarity.
    
    Args:
        videos_data: List of text documents
        shortcodes: List of video shortcodes
        metadata: Dict with video metadata
        selected_topics: List of topic names to use
        base_dir: Base directory for output
    
    Returns:
        dict: Category assignments
    """
    print(f"\n{'='*70}")
    print(f"🎯 CLASSIFYING VIDEOS INTO {len(selected_topics)} CATEGORIES")
    print(f"{'='*70}\n")
    
    base_dir = os.path.expanduser(base_dir)
    
    # Build keyword sets for each topic
    topic_keywords = {}
    for topic in selected_topics:
        # Check if it's a predefined topic
        if topic in TOPIC_KEYWORDS:
            topic_keywords[topic] = [k.lower() for k in TOPIC_KEYWORDS[topic]]
        else:
            # Generate keywords from topic name
            words = re.findall(r'\b[a-zA-ZäöüßÄÖÜ]{3,}\b', topic.lower())
            topic_keywords[topic] = words
    
    # Classify each video
    categories = defaultdict(list)
    unclassified = []
    manual_kept = 0
    auto_classified = 0
    
    for idx, (text, shortcode) in enumerate(zip(videos_data, shortcodes)):
        video_dir = os.path.join(base_dir, shortcode)
        category_file = os.path.join(video_dir, 'category.json')
        
        # Check if manual category.json exists and should be preserved
        existing_category = None
        if os.path.exists(category_file):
            try:
                with open(category_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # Preserve if manually edited
                    if existing_data.get('manual', False):
                        existing_category = existing_data.get('category')
                        manual_kept += 1
            except (json.JSONDecodeError, IOError):
                pass
        
        if existing_category:
            # Use manually set category
            categories[existing_category].append({
                'shortcode': shortcode,
                'score': 999,  # High score for manual
                'matched_keywords': ['manual'],
                'metadata': metadata.get(shortcode, {}),
                'manual': True
            })
            continue
        
        text_lower = text.lower()
        
        # Score each topic
        topic_scores = []
        for topic, keywords in topic_keywords.items():
            score = 0
            matched = []
            for keyword in keywords:
                # Use word boundary matching for better precision
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Weight by keyword length (longer = more specific) and frequency
                    score += len(keyword) * len(matches)
                    matched.append(keyword)
            if score > 0:
                topic_scores.append((topic, score, matched))
        
        if topic_scores:
            # Assign to best matching topic
            topic_scores.sort(key=lambda x: x[1], reverse=True)
            best_topic, score, matched = topic_scores[0]
            categories[best_topic].append({
                'shortcode': shortcode,
                'score': score,
                'matched_keywords': matched[:5],
                'metadata': metadata.get(shortcode, {}),
                'manual': False
            })
            auto_classified += 1
            
            # Save category.json in video subdirectory
            _save_video_category(video_dir, shortcode, best_topic, score, matched[:5], False)
        else:
            unclassified.append(shortcode)
            # Save as uncategorized
            _save_video_category(video_dir, shortcode, 'Other / Uncategorized', 0, [], False)
    
    # Add "Other" category for unclassified
    if unclassified:
        categories['Other / Uncategorized'] = [
            {'shortcode': sc, 'score': 0, 'matched_keywords': [], 'metadata': metadata.get(sc, {}), 'manual': False}
            for sc in unclassified
        ]
    
    # Print results
    print(f"Classification complete!\n")
    print(f"  📊 Auto-classified: {auto_classified} videos")
    print(f"  ✋ Manual preserved: {manual_kept} videos")
    print()
    
    sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    
    for topic, videos in sorted_cats:
        manual_count = sum(1 for v in videos if v.get('manual', False))
        manual_str = f" ({manual_count} manual)" if manual_count > 0 else ""
        print(f"  📁 {topic}: {len(videos)} videos{manual_str}")
    
    if unclassified:
        print(f"\n  ⚠️  {len(unclassified)} videos couldn't be classified")
        print(f"\n  💡 Sample uncategorized videos (for adding custom topics):")
        import random
        sample_unclassified = random.sample(unclassified, min(5, len(unclassified)))
        for sc in sample_unclassified:
            meta = metadata.get(sc, {})
            # Show transcript if available, otherwise post excerpt
            excerpt = meta.get('transcript', '') or meta.get('post_excerpt', '')
            if not excerpt:
                excerpt = meta.get('full_transcript', meta.get('full_post', ''))[:100]
            print(f"     • {sc}: {excerpt[:100]}...")
    
    # Save main results
    output_file = os.path.join(base_dir, 'categories.json')
    
    export_data = {}
    for topic, videos in categories.items():
        export_data[topic] = {
            'size': len(videos),
            'videos': [
                {
                    'shortcode': v['shortcode'],
                    'score': v['score'],
                    'url': f"https://www.instagram.com/reel/{v['shortcode']}",
                    'matched_keywords': v['matched_keywords'],
                    'tags': v['metadata'].get('tags', []),
                    'has_transcript': v['metadata'].get('has_transcript', False),
                    'manual': v.get('manual', False)
                }
                for v in sorted(videos, key=lambda x: x['score'], reverse=True)
            ]
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_file}")
    print(f"✅ Individual category.json files saved in each video directory")
    print(f"   (Edit 'manual': true to preserve your changes)")
    
    return categories


def _save_video_category(video_dir, shortcode, category, score, matched_keywords, manual=False):
    """
    Save category.json in a video's subdirectory.
    
    Args:
        video_dir: Path to video directory
        shortcode: Video shortcode
        category: Assigned category name
        score: Classification score
        matched_keywords: Keywords that matched
        manual: Whether this was manually set
    """
    category_file = os.path.join(video_dir, 'category.json')
    
    # Check if manual category exists - don't overwrite
    if os.path.exists(category_file):
        try:
            with open(category_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                if existing.get('manual', False):
                    return  # Don't overwrite manual edits
        except (json.JSONDecodeError, IOError):
            pass
    
    category_data = {
        'shortcode': shortcode,
        'category': category,
        'score': score,
        'matched_keywords': matched_keywords,
        'manual': manual,
        'url': f"https://www.instagram.com/reel/{shortcode}"
    }
    
    try:
        with open(category_file, 'w', encoding='utf-8') as f:
            json.dump(category_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        pass  # Silently fail if can't write


def determine_optimal_clusters(tfidf_matrix, max_clusters=20):
    """
    Determine optimal number of clusters using silhouette score.
    
    Args:
        tfidf_matrix: TF-IDF matrix
        max_clusters: Maximum number of clusters to try
    
    Returns:
        int: Optimal number of clusters
    """
    n_samples = tfidf_matrix.shape[0]
    max_k = min(max_clusters, n_samples // 3)  # At least 3 items per cluster on average
    
    if max_k < 2:
        return 2
    
    print(f"\n🔍 Determining optimal number of categories (testing 2-{max_k})...")
    
    best_score = -1
    best_k = max_k // 2
    scores = []
    
    for k in range(2, min(max_k + 1, 16)):  # Don't test too many to save time
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(tfidf_matrix)
        
        # Calculate silhouette score
        score = silhouette_score(tfidf_matrix, cluster_labels, sample_size=min(1000, n_samples))
        scores.append((k, score))
        
        if score > best_score:
            best_score = score
            best_k = k
        
        print(f"  k={k:2d}: silhouette score = {score:.3f}")
    
    print(f"\n✓ Optimal number of categories: {best_k} (score: {best_score:.3f})")
    return best_k


def categorize_videos(base_dir, num_categories=None, min_cluster_size=3, auto_detect=True):
    """
    Analyze all processed videos and categorize them into themes.
    
    Args:
        base_dir (str): Base directory containing reel subdirectories.
        num_categories (int, optional): Number of categories. If None, auto-detects.
        min_cluster_size (int): Minimum videos per category to display.
        auto_detect (bool): Whether to auto-detect optimal number of clusters.
    
    Returns:
        dict: Dictionary mapping category names to video lists.
    """
    # Collect data
    videos_data, shortcodes, metadata = collect_video_data(base_dir)
    
    if len(videos_data) < 2:
        print("❌ Not enough videos to categorize (need at least 2)")
        return {}
    
    # Vectorize text with TF-IDF
    print(f"\n{'='*70}")
    print(f"📊 Analyzing content with TF-IDF vectorization...")
    print(f"{'='*70}\n")
    
    vectorizer = TfidfVectorizer(
        max_features=400,  # Increased for better content capture
        min_df=3,  # Must appear in at least 3 videos (reduce noise)
        max_df=0.7,  # Ignore terms in >70% of videos (too common)
        ngram_range=(1, 4),  # Up to 4-word phrases for specific topics
        stop_words=list(EXTENDED_STOP_WORDS),  # Custom English + German stop words
        token_pattern=r'\b[a-zA-ZäöüßÄÖÜ]{3,}\b',  # Min 3 chars, include German chars
        lowercase=True
    )
    
    tfidf_matrix = vectorizer.fit_transform(videos_data)
    feature_names = vectorizer.get_feature_names_out()
    
    print(f"✓ Created TF-IDF matrix: {tfidf_matrix.shape[0]} videos × {tfidf_matrix.shape[1]} features")
    print(f"  Sample features: {', '.join(feature_names[:10])}")
    
    # Determine number of clusters
    if num_categories is None and auto_detect:
        num_categories = determine_optimal_clusters(tfidf_matrix)
    elif num_categories is None:
        num_categories = max(2, len(videos_data) // 10)  # ~10 videos per category
        print(f"\n💡 Using {num_categories} categories (~{len(videos_data)//num_categories} videos per category)")
    else:
        if num_categories > len(videos_data) // 2:
            num_categories = max(2, len(videos_data) // 2)
            print(f"\n⚠️  Reduced to {num_categories} categories (only {len(videos_data)} videos available)")
    
    # Perform K-means clustering
    print(f"\n{'='*70}")
    print(f"🎯 Clustering into {num_categories} categories...")
    print(f"{'='*70}\n")
    
    kmeans = KMeans(n_clusters=num_categories, random_state=42, n_init=20)
    cluster_labels = kmeans.fit_predict(tfidf_matrix)
    
    # Analyze each cluster
    categories = {}
    
    for cluster_id in range(num_categories):
        cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
        
        if len(cluster_indices) < min_cluster_size:
            continue
        
        # Get top terms for this cluster
        cluster_center = kmeans.cluster_centers_[cluster_id]
        top_term_indices = cluster_center.argsort()[-20:][::-1]  # Get top 20 for better selection
        top_terms = [feature_names[i] for i in top_term_indices]
        
        # Generate readable category name from top terms
        category_name = create_readable_category_name(top_terms, min_words=2, max_words=3)
        
        # Collect videos with relevance scores
        videos_in_category = []
        for idx in cluster_indices:
            shortcode = shortcodes[idx]
            video_vector = tfidf_matrix[idx].toarray().flatten()
            similarity = np.dot(video_vector, cluster_center) / (
                np.linalg.norm(video_vector) * np.linalg.norm(cluster_center) + 1e-10
            )
            videos_in_category.append((shortcode, similarity))
        
        videos_in_category.sort(key=lambda x: x[1], reverse=True)
        
        categories[category_name] = {
            'videos': videos_in_category,
            'top_terms': top_terms,
            'size': len(cluster_indices)
        }
    
    # Print results
    print(f"\n{'='*70}")
    print(f"📋 CATEGORIZATION RESULTS")
    print(f"{'='*70}\n")
    print(f"Total videos analyzed: {len(videos_data)}")
    print(f"Categories discovered: {len(categories)}")
    print(f"Average videos per category: {len(videos_data) // len(categories) if categories else 0}\n")
    
    sorted_categories = sorted(categories.items(), key=lambda x: x[1]['size'], reverse=True)
    
    for idx, (category_name, data) in enumerate(sorted_categories, 1):
        print(f"\n{'─'*70}")
        print(f"📁 Category #{idx}: {category_name.upper()}")
        print(f"{'─'*70}")
        print(f"Size: {data['size']} videos")
        print(f"Related terms: {', '.join(data['top_terms'][:12])}")
        
        print(f"\n🎬 Top 5 videos (by relevance):")
        for i, (shortcode, score) in enumerate(data['videos'][:5], 1):
            url = f"https://www.instagram.com/reel/{shortcode}"
            meta = metadata.get(shortcode, {})
            
            # Show a snippet of what makes this video relevant
            snippet = ""
            if meta.get('tags'):
                snippet = f"Tags: {', '.join(meta['tags'][:3])}"
            elif meta.get('transcript'):
                snippet = f"Transcript: {meta['transcript'][:80]}..."
            
            print(f"  {i}. {shortcode} (score: {score:.3f})")
            print(f"     {url}")
            if snippet:
                print(f"     {snippet}")
    
    # Save to JSON
    base_dir = os.path.expanduser(base_dir)
    output_file = os.path.join(base_dir, 'categories.json')
    
    categories_export = {}
    for category_name, data in categories.items():
        categories_export[category_name] = {
            'size': data['size'],
            'top_terms': data['top_terms'],
            'videos': [
                {
                    'shortcode': sc,
                    'score': float(score),
                    'url': f"https://www.instagram.com/reel/{sc}",
                    'tags': metadata.get(sc, {}).get('tags', []),
                    'has_transcript': metadata.get(sc, {}).get('has_transcript', False)
                }
                for sc, score in data['videos']
            ]
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categories_export, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✅ Categorization saved to: {output_file}")
    print(f"{'='*70}\n")
    
    return categories


def main():
    parser = argparse.ArgumentParser(
        description="Categorize Instagram Reels by analyzing transcripts, tags, and descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - discover topics and choose which to use
  python cluster_reel_videos.py --dir ~/reel_archive --interactive

  # Use predefined categories
  python cluster_reel_videos.py --dir ~/reel_archive --categories "Triathlon,Comedy,Parenting,Cooking"

  # Auto-detect optimal number of categories (legacy mode)
  python cluster_reel_videos.py --dir ~/reel_archive

  # Specify number of categories manually
  python cluster_reel_videos.py --dir ~/reel_archive --num-categories 12
        """
    )
    
    parser.add_argument(
        '--dir',
        default=os.path.expanduser('~/reel_archive'),
        help='Directory containing processed reels (default: ~/reel_archive)'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode: discover topics and let you choose which to use'
    )
    parser.add_argument(
        '--categories', '-c',
        type=str,
        default=None,
        help='Comma-separated list of categories to use (e.g., "Triathlon,Comedy,Parenting")'
    )
    parser.add_argument(
        '--discover-only',
        action='store_true',
        help='Only discover topics, don\'t classify videos'
    )
    parser.add_argument(
        '--suggest-more',
        type=str,
        default=None,
        help='Suggest additional categories based on provided selection (e.g., "Running,Comedy,Parenting")'
    )
    parser.add_argument(
        '--fine-tune',
        action='store_true',
        help='Learn from manual:true entries to improve classification'
    )
    parser.add_argument(
        '--show-learned',
        action='store_true',
        help='Show what has been learned from manual categorizations'
    )
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List all predefined categories from TOPIC_KEYWORDS and exit'
    )
    parser.add_argument(
        '--all-categories',
        action='store_true',
        help='Use all predefined categories from TOPIC_KEYWORDS (same as --categories with all topics)'
    )
    parser.add_argument(
        '--num-categories',
        type=int,
        default=None,
        help='Number of categories for auto-clustering (legacy mode)'
    )
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        default=3,
        help='Minimum videos per category (default: 3)'
    )
    parser.add_argument(
        '--no-auto-detect',
        action='store_true',
        help='Disable automatic detection of optimal cluster count'
    )
    
    args = parser.parse_args()
    
    # Handle --all-categories by setting args.categories to all predefined topics
    if args.all_categories:
        args.categories = ",".join(TOPIC_KEYWORDS.keys())
        print(f"📋 Using all {len(TOPIC_KEYWORDS)} predefined categories")
    
    # Mode: List available categories
    if args.list_categories:
        print(f"\n{'='*70}")
        print("📋 AVAILABLE PREDEFINED CATEGORIES")
        print(f"{'='*70}\n")
        
        sorted_topics = sorted(TOPIC_KEYWORDS.keys())
        
        for i, topic in enumerate(sorted_topics, 1):
            keywords = TOPIC_KEYWORDS[topic][:5]
            keywords_str = ", ".join(keywords)
            print(f"  {i:2d}. {topic:<25} [{keywords_str}]")
        
        print(f"\n{'─'*70}")
        print(f"Total: {len(TOPIC_KEYWORDS)} predefined categories\n")
        print("Usage: --categories \"Category1,Category2,Category3\"")
        print(f"{'='*70}\n")
        sys.exit(0)
    
    try:
        # Collect video data first
        videos_data, shortcodes, metadata = collect_video_data(args.dir)
        
        if len(videos_data) < 2:
            print("❌ Not enough videos to categorize (need at least 2)")
            sys.exit(1)
        
        # Mode 0: Discovery only
        if args.discover_only:
            discovered_topics = discover_all_topics(videos_data)
            
            # Print all discovered topics
            print(f"\n{'='*70}")
            print("📋 ALL DISCOVERED TOPICS")
            print(f"{'='*70}\n")
            
            for i, (name, keywords, count) in enumerate(discovered_topics, 1):
                keywords_str = ", ".join(keywords[:5])
                print(f"  {i:2d}. {name:<30} (~{count:3d} videos)  [{keywords_str}]")
            
            print("\n✅ Topic discovery complete!")
            sys.exit(0)
        
        # Mode 0.5: Suggest more categories
        if args.suggest_more:
            selected = [c.strip() for c in args.suggest_more.split(',')]
            suggestions = suggest_additional_categories(selected, videos_data, num_suggestions=20)
            print("\n✅ Suggestions complete!")
            sys.exit(0)
        
        # Mode 0.6: Show learned keywords
        if args.show_learned:
            learned = fine_tune_classification(args.dir, videos_data, shortcodes, metadata, [])
            print("\n✅ Learning analysis complete!")
            sys.exit(0)
        
        # Mode 1: Interactive topic selection
        if args.interactive:
            discovered_topics = discover_all_topics(videos_data)
            
            if args.discover_only:
                print("\n✅ Topic discovery complete!")
                sys.exit(0)
            
            selected_topics = interactive_topic_selection(discovered_topics, videos_data)
            
            if args.fine_tune:
                learned_keywords = learn_from_manual_categories(args.dir, videos_data, shortcodes, metadata)
                if learned_keywords:
                    categories = classify_with_fine_tuning(
                        videos_data, shortcodes, metadata, selected_topics, args.dir, learned_keywords
                    )
                else:
                    categories = classify_videos_by_topics(
                        videos_data, shortcodes, metadata, selected_topics, args.dir
                    )
            else:
                categories = classify_videos_by_topics(
                    videos_data, shortcodes, metadata, selected_topics, args.dir
                )
        
        # Mode 2: Predefined categories
        elif args.categories:
            selected_topics = [c.strip() for c in args.categories.split(',')]
            print(f"\n📋 Using predefined categories: {', '.join(selected_topics)}")
            
            if args.fine_tune:
                learned_keywords = learn_from_manual_categories(args.dir, videos_data, shortcodes, metadata)
                if learned_keywords:
                    categories = classify_with_fine_tuning(
                        videos_data, shortcodes, metadata, selected_topics, args.dir, learned_keywords
                    )
                else:
                    categories = classify_videos_by_topics(
                        videos_data, shortcodes, metadata, selected_topics, args.dir
                    )
            else:
                categories = classify_videos_by_topics(
                    videos_data, shortcodes, metadata, selected_topics, args.dir
                )
        
        # Mode 3: Legacy auto-clustering
        else:
            categories = categorize_videos(
                args.dir,
                num_categories=args.num_categories,
                min_cluster_size=args.min_cluster_size,
                auto_detect=not args.no_auto_detect
            )
        
        if categories:
            print("\n" + "="*70)
            print("✅ Categorization complete!")
            print("="*70 + "\n")
            sys.exit(0)
        else:
            print("❌ No categories created")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
