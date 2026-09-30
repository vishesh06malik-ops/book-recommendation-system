# Project Statement — BookWise

**Course:** Python Essentials (VITyarthi — Evaluated Course Project)
**Project:** BookWise — Smart Book Discovery & Recommendation System

## Problem Statement

Readers find it hard to choose their next book from thousands of titles. Bestseller
lists show the same popular books to everyone, and most recommendation platforms do not
explain *why* a book is suggested. Many also need an account and an internet connection.

BookWise solves this with a Python command-line application. It lets a reader search a real,
public dataset of 10,000 books, browse genres, and get **explainable** recommendations:
books similar to a chosen book, and books personalised to the reader's favourites, ratings
and preferred genres. It all works offline and needs no API key.

## Scope of the Project

**In scope**
- Loading, validating and cleaning the public goodbooks-10k dataset (CC BY-SA 4.0)
- Searching by title, author, genre, ISBN and keyword, and browsing by genre
- Book details, with "Not available" shown for missing data (no invented values)
- A content-based recommender written in plain Python (weighted Jaccard similarity on
  keywords, genres, authors and title words), with an explanation for every result
- Favourites, personal 1–5 ratings, genre preferences and viewing history, saved in a local
  JSON file
- Personalised recommendations based on these preferences
- Optional enhancements: a TF-IDF + cosine-similarity recommender (scikit-learn), live
  search through the Google Books API, and a Streamlit web interface
- Automated tests with pytest

**Out of scope**
- User accounts, logins or multiple users sharing one installation
- Collaborative filtering ("readers like you also liked…")
- Buying, borrowing or reading books inside the application
- Measuring recommendation accuracy against real users (no labelled data is available)

## Target Users

- Students and casual readers looking for their next book
- Readers who want to know *why* a book is recommended
- Beginners in Python who want a readable example of a small recommendation system

## High-Level Features

1. **Book Search & Discovery:** search in five modes, browse 22 genres, view full book details
2. **Recommendation Engine:** top 5/10/15 similar books, with the selected book and duplicate
   editions removed, and a reason for each result
3. **User Preferences & Personalisation:** favourites, ratings, preferred genres, and
   personalised recommendations with explanations
4. **Reliable local storage:** safe (atomic) JSON saving, and a corrupted file is backed up
   instead of crashing the app
5. **Robust input handling:** invalid menu choices, numbers, ratings and empty searches never crash
   the program
6. **Optional extras:** TF-IDF recommender, Google Books live search, Streamlit web UI. The
   core works without any of them.
