import numpy as np
import pandas as pd
import datetime
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import bs4 as bs
import urllib.request
import pickle
import requests
from tmdbv3api import Movie
from tmdbv3api import TMDb
from werkzeug.utils import redirect
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY')
data = 'data/Movies.csv'
print(tmdb.api_key)

# Load movie data 
movies_df = pd.read_csv(data)

def create_similarity(data):
    # creating a count matrix
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(movies_df['comb'])
    # creating a similarity score matrix
    similar = cosine_similarity(count_matrix)
    return similar

def find_recommendation(title,data):
    title = title.lower()
    try:
        similarity.shape
    except:
        similarity = create_similarity(data)

    if title not in movies_df['movie_title'].unique():
        return('Sorry! The movie your searched is not in our database. Please check the spelling or try with some other movies')
    else:
        idx = movies_df.loc[movies_df['movie_title']==title].index[0]
        lst = list(enumerate(similarity[idx]))
        lst = sorted(lst, key = lambda x:x[1] ,reverse=True)
        lst = lst[1:11]
        l = []
        for each in lst:
            movie_idx = each[0]
            l.append(movies_df['movie_title'][movie_idx])
        return l

def list_of_genres(genre_json):
    if genre_json:
        genres = []
        genre_str = ", " 
        for i in range(0,len(genre_json)):
            genres.append(genre_json[i]['name'])
        return genre_str.join(genres)

def date_convert(date):
    date = pd.to_datetime(date)
    day = date.day
    year = date.year
    month = datetime.datetime.strptime("{}".format(date.month), "%m").strftime("%B")
    return day,month,year

def movie_runtime(duration):
    if duration%60==0:
        return "{:.0f} hours".format(duration/60)
    else:
        return "{:.0f} hours {} minutes".format(duration/60,duration%60)



@app.route("/",methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if request.method == "POST":
        movie_name = request.form.get("movie_name")
    else:  # Handle GET request when clicking a recommended movie
        movie_name = request.args.get("movie_name")

    if not movie_name:
        return redirect("/")

    recommended_movies = find_recommendation(movie_name, data)
    movie_name = movie_name.upper()

    if isinstance(recommended_movies, str):
        return redirect("/")
    
    tmdb_movie_object = Movie()
    movie_list = tmdb_movie_object.search(movie_name)

    if not movie_list:
        return redirect("/")

    movie_id = movie_list[0].id
    response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb.api_key}')
    movie_json = response.json()

    poster_path = movie_json.get('poster_path', '')
    img_path = f'https://image.tmdb.org/t/p/original{poster_path}'
    movie_name = movie_json['title']
    lang = movie_json['original_language']
    overview = movie_json['overview']
    genre = list_of_genres(movie_json.get('genres', []))
    rating = movie_json['vote_average']
    vote_count = f"{movie_json['vote_count']:,}"
    release_day, release_month, release_year = date_convert(movie_json['release_date'])
    release_date = f"{release_month} {release_day}, {release_year}"
    runtime = movie_runtime(movie_json['runtime'])

    recommended_list = []
    for movie_title in recommended_movies:
        movie_dict = {}
        result = tmdb_movie_object.search(movie_title)
        if not result:
            continue  # Skip if no results found

        movie_id = result[0].id
        responses = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb.api_key}')
        movies_json = responses.json()
        movie_dict['Movie_name'] = movies_json['title']
        movie_dict['Duration'] = movie_runtime(movies_json['runtime'])
        movie_dict['Rating'] = movies_json['vote_average']
        movie_dict['Image'] = f'https://image.tmdb.org/t/p/original{movies_json.get("poster_path", "")}'
        r_day, r_month, r_year = date_convert(movies_json['release_date'])
        movie_dict['Year'] = r_year
        recommended_list.append(movie_dict)

    return render_template('recommend.html', movie_name=movie_name, language=lang, movie_year=release_year, 
                           img_path=img_path, rating=rating, overview=overview, release_date=release_date, 
                           genre=genre, vote_count=vote_count, runtime=runtime, result_list=recommended_list)
    
@app.route("/search_suggestions", methods=["GET"])
def search_suggestions():
    query = request.args.get("query", "").lower()
    if not query:
        return jsonify([])

    suggestions = movies_df[movies_df["movie_title"].str.lower().str.contains(query, na=False)]["movie_title"].tolist()[:9]
    return jsonify(suggestions)

if __name__ == "__main__":
    app.run()

