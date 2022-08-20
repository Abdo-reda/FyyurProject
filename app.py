#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from asyncio.windows_events import NULL
from email.policy import default
import json
from sys import set_coroutine_origin_tracking_depth
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate
from forms import *
import numpy as np #was used to convert between arrays and lists.
from flask import abort
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#the database connection is established in the config.py file.

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#



class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    #genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    website_link = db.Column(db.String(120)) 
    seekFlag = db.Column(db.Boolean, default=False)
    seekAd = db.Column(db.String)
    shows = db.relationship('Shows', backref='venue', lazy=True)
    genres = db.Column(db.ARRAY(db.String, dimensions=1))





class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    #genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    website_link = db.Column(db.String(120))
    seekFlag = db.Column(db.Boolean, default=False)
    seekAd = db.Column(db.String)
    shows = db.relationship('Shows', backref='artist', lazy=True)
    genres = db.Column(db.ARRAY(db.String, dimensions=1))


class Shows(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
 
 




#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  #Get a hold of the venue list.
  venueList = Venue.query.order_by('id').all()

  #The data we want to finally send is a list of dictionairies which themselves contain a list of dicionaries (venues), 
  #I will create the structure of that dicionary in the following class, and append it to our data object.
  class AddressStruct:
    def __init__(self, city, state):
      self.dict = {
        "city": city,
        "state": state,
        "venues": []
      }

  #This is the structure of the dictionary in the venues list in the data list.
  class VenueStruct:
    def __init__(self, id, name, numUpShows):
      self.dict = {
        "id": id,
        "name": name,
        "numUpShows": numUpShows
      }

  

  #Loop over the venues in the list, calculate number of upcoming shows.
  data = []
  for curVenue in venueList:
    #calculate the number of upcoming SHOWS
    showsList = Shows.query.filter(Shows.venue_id==curVenue.id)
    numOfUp = 0
    for curShow in showsList:
      showTime = curShow.time
      curTime = datetime.now()
      if(showTime > curTime):
        numOfUp = numOfUp+1

    #Create a Venue Obj
    venueObj = VenueStruct(curVenue.id, curVenue.name, numOfUp)

    #loop over our address dictionaries and insert our venue obj. We need to make sure that we don't duplicate dictionaries with the same city and state.
    addressExist = False
    for curAddress in data:
      if(curAddress['city'] == curVenue.city and curAddress['state']==curVenue.state):
        curAddress['venues'].append(venueObj.dict)
        addressExist = True
      
    if(not(addressExist)):
      addressObj = AddressStruct(curVenue.city, curVenue.state)
      addressObj.dict['venues'].append(venueObj.dict)
      data.append(addressObj.dict)

  return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():

  class VenueStruct:
    def __init__(self, id, name, numUpShows):
      self.dict = {
        "id": id,
        "name": name,
        "numUpShows": numUpShows
      }
  #get search term and perform query
  searchTerm=request.form.get('search_term', '')
  venueList = Venue.query.filter(Venue.name.ilike('%'+searchTerm+'%')).all()
 
  #loop through venue list and create our data list
  tempData = []
  for curVenue in venueList:
    #calculate the number of upcoming SHOWS
    showsList = Shows.query.filter(Shows.venue_id==curVenue.id)
    numOfUp = 0
    for curShow in showsList:
      showTime = curShow.time
      curTime = datetime.now()
      if(showTime > curTime):
        numOfUp = numOfUp+1

    #Create a Venue Obj
    venueObj = VenueStruct(curVenue.id, curVenue.name, numOfUp)
    tempData.append(venueObj.dict)

  #Create our response objct
  response={
    "count": len(tempData),
    "data": tempData
  }

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  curVenue = Venue.query.get(venue_id)

  #--------Doing show stuff
  class ShowStruct:
    def __init__(self, artist_id, artist_name, artist_image_link, start_time):
      self.dict = {
        "artist_id": artist_id,
        "artist_name": artist_name,
        "artist_image_link": artist_image_link,
        "start_time": start_time.strftime("%Y/%m/%d, %H:%M:%S")
      }
  
  #show list of the venue, loop over them, and check which ones are upcoming and which ones are in the past.
  showsList = Shows.query.filter(Shows.venue_id==curVenue.id)
  pastShows =[]
  upcomingShows=[]
  for curShow in showsList:
    tempArtist = Artist.query.get(curShow.artist_id)
    showObj = ShowStruct(curShow.artist_id, tempArtist.name, tempArtist.image_link, curShow.time)
    showTime = curShow.time
    curTime = datetime.now()
    if(showTime > curTime):
      upcomingShows.append(showObj.dict)
    else:
      pastShows.append(showObj.dict)

  
  data={
    "id": curVenue.id,
    "name": curVenue.name,
    "genres": np.array(curVenue.genres),
    "address": curVenue.address,
    "city": curVenue.city,
    "state": curVenue.state,
    "phone": curVenue.phone,
    "website": curVenue.website_link,
    "facebook_link": curVenue.facebook_link,
    "seeking_talent": curVenue.seekFlag,
    "seeking_description": curVenue.seekAd,
    "image_link": curVenue.image_link,
    "past_shows": pastShows,
    "upcoming_shows": upcomingShows,
    "past_shows_count": len(pastShows),
    "upcoming_shows_count": len(upcomingShows),
  }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  #body = {}
  try:
      myVenue = Venue()
      myVenue.name=request.form['name']
      myVenue.city=request.form['city']
      myVenue.state=request.form['state']
      myVenue.address=request.form['address']
      myVenue.phone=request.form['phone']
      genreList = request.form.getlist('genres')
      myVenue.genres=np.array(genreList)
      myVenue.facebook_link=request.form['facebook_link']
      myVenue.image_link=request.form['image_link']
      myVenue.website_link=request.form['website_link']
      if 'seeking_talent' in request.form.keys() :
        myVenue.seekFlag=True
      else:
        myVenue.seekFlag=False
      myVenue.seekAd=request.form['seeking_description']
      db.session.add(myVenue)
      db.session.commit()
      #body['description'] = myVenue.description
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Venue ' + request.form['name'] + ' failed to be listed!')
        #abort(400)
      else:
         flash('Venue ' + request.form['name'] + ' was successfully listed!')
      # STILL: modify data to be the data object returned from db insertion
      # on successful db insert, flash success
      return render_template('pages/home.html', data=myVenue)



@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  #STILL: Complete this endpoint for taking a venue_id, and using
  #SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False
  try:
      curVenue = Venue.query.get(venue_id)
      db.session.delete(curVenue)
      db.session.commit()
      #I am not sure what the default behaviour and what will happen to children when I delete a venue.
      #I can define the behaviour on db.relationship cascade="all, delete-orphan", cascade="all, delete"
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Venue ' + request.form['name'] + ' couldnt be removed!')
        #abort(400)
      else:
         flash('Venue ' + request.form['name'] + ' was successfully removed!')
      
      return render_template('pages/home.html')

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artistList = Artist.query.order_by('id').all()

  class ArtistStruct:
    def __init__(self, id, name):
      self.dict = {
        "id": id,
        "name": name,
      }

  #Fill Data Object
  data = []
  for curArtist in artistList: 
    #Create a Artist Obj
    artistObj = ArtistStruct(curArtist.id, curArtist.name)
    data.append(artistObj.dict)

  return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
  
  class ArtistStruct:
    def __init__(self, id, name, numUpShows):
      self.dict = {
        "id": id,
        "name": name,
        "numUpShows": numUpShows
      }
  #get search term and perform query
  searchTerm=request.form.get('search_term', '')
  artistList = Artist.query.filter(Artist.name.ilike('%'+searchTerm+'%')).all()
 
  #loop through venue list and create our data list
  tempData = []
  for curArtist in artistList:
    #calculate the number of upcoming SHOWS
    showsList = Shows.query.filter(Shows.artist_id==curArtist.id)
    numOfUp = 0
    for curShow in showsList:
      showTime = curShow.time
      curTime = datetime.now()
      if(showTime > curTime):
        numOfUp = numOfUp+1

    #Create a Artist Obj
    artistObj = ArtistStruct(curArtist.id, curArtist.name, numOfUp)
    tempData.append(artistObj.dict)

  #Create our response objct
  response={
    "count": len(tempData),
    "data": tempData
  }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  curArtist = Artist.query.get(artist_id)

  #--------Doing show stuff
  class ShowStruct:
    def __init__(self, venue_id, venue_name, venue_image_link, start_time):
      self.dict = {
        "venue_id": venue_id,
        "venue_name": venue_name,
        "venue_image_link": venue_image_link,
        "start_time": start_time.strftime("%Y/%m/%d, %H:%M:%S")
      }
  
  #show list of the venue
  showsList = Shows.query.filter(Shows.artist_id==curArtist.id)
  pastShows =[]
  upcomingShows=[]
  for curShow in showsList:
    tempVenue = Venue.query.get(curShow.venue_id)
    showObj = ShowStruct(curShow.venue_id, tempVenue.name, tempVenue.image_link, curShow.time)
    showTime = curShow.time
    curTime = datetime.now()
    if(showTime > curTime):
      upcomingShows.append(showObj.dict)
    else:
      pastShows.append(showObj.dict)

  
  data={
    "id": curArtist.id,
    "name": curArtist.name,
    "genres": np.array(curArtist.genres),
    "city": curArtist.city,
    "state": curArtist.state,
    "phone": curArtist.phone,
    "website": curArtist.website_link,
    "facebook_link": curArtist.facebook_link,
    "seeking_venue": curArtist.seekFlag,
    "seeking_description": curArtist.seekAd,
    "image_link": curArtist.image_link,
    "past_shows": pastShows,
    "upcoming_shows": upcomingShows,
    "past_shows_count": len(pastShows),
    "upcoming_shows_count": len(upcomingShows),
  }

  return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  curArtist = Artist.query.get(artist_id)
  artist={
    "id": curArtist.id,
    "name": curArtist.name,
    "genres": np.array(curArtist.genres),
    "city": curArtist.city,
    "state": curArtist.state,
    "phone": curArtist.phone,
    "website": curArtist.website_link,
    "facebook_link": curArtist.facebook_link,
    "seeking_venue": curArtist.seekFlag,
    "seeking_description": curArtist.seekAd,
    "image_link": curArtist.image_link
  }

  form.name.data = artist['name']
  form.genres.data = artist['genres']
  form.city.data = artist['city']
  form.state.data = artist['state']
  form.phone.data = artist['phone']
  form.website_link.data = artist['website']
  form.facebook_link.data = artist['facebook_link']
  form.seeking_venue.data = artist['seeking_venue']
  form.seeking_description.data = artist['seeking_description']
  form.image_link.data = artist['image_link']

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

  error = False
  try:
      curArtist = Artist.query.get(artist_id)
      curArtist.name=request.form['name']
      curArtist.city=request.form['city']
      curArtist.state=request.form['state']
      curArtist.phone=request.form['phone']
      genreList = request.form.getlist('genres')
      curArtist.genres=np.array(genreList)
      curArtist.facebook_link=request.form['facebook_link']
      curArtist.image_link=request.form['image_link']
      curArtist.website_link=request.form['website_link']
      if 'seeking_venue' in request.form.keys() :
        curArtist.seekFlag=True
      else:
        curArtist.seekFlag=False
      curArtist.seekAd=request.form['seeking_description']
      db.session.commit()
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Artist ' + request.form['name'] + ' failed to be updated!')
        #abort(400)
      else:
         flash('Artist ' + request.form['name'] + ' was successfully updated!')
     
      return redirect(url_for('show_artist', artist_id=artist_id))



@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  
  curVenue = Venue.query.get(venue_id)
  venue={
    "id": curVenue.id,
    "name": curVenue.name,
    "genres":  np.array(curVenue.genres),
    "address": curVenue.address,
    "city": curVenue.city,
    "state": curVenue.state,
    "phone": curVenue.phone,
    "website": curVenue.website_link,
    "facebook_link": curVenue.facebook_link,
    "seeking_talent": curVenue.seekFlag,
    "seeking_description": curVenue.seekAd,
    "image_link": curVenue.image_link
  }

  form.name.data = venue['name']
  form.genres.data = venue['genres']
  form.address.data = venue['address']
  form.city.data = venue['city']
  form.state.data = venue['state']
  form.phone.data = venue['phone']
  form.website_link.data = venue['website']
  form.facebook_link.data = venue['facebook_link']
  form.seeking_talent.data = venue['seeking_talent']
  form.seeking_description.data = venue['seeking_description']
  form.image_link.data = venue['image_link']

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  error = False
  try:
      curVenue = Venue.query.get(venue_id)
      curVenue.name=request.form['name']
      curVenue.city=request.form['city']
      curVenue.state=request.form['state']
      curVenue.address=request.form['address']
      curVenue.phone=request.form['phone']
      genreList = request.form.getlist('genres')
      curVenue.genres=np.array(genreList)
      curVenue.facebook_link=request.form['facebook_link']
      curVenue.image_link=request.form['image_link']
      curVenue.website_link=request.form['website_link']
      if 'seeking_talent' in request.form.keys() :
        curVenue.seekFlag=True
      else:
        curVenue.seekFlag=False
      curVenue.seekAd=request.form['seeking_description']
      db.session.commit()
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Venue ' + request.form['name'] + ' failed to be created!')
        #abort(400)
      else:
         flash('Venue ' + request.form['name'] + ' was successfully created!')

      return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  #body = {}
  try:
      myArtist = Artist()
      myArtist.name=request.form['name']
      myArtist.city=request.form['city']
      myArtist.state=request.form['state']
      myArtist.phone=request.form['phone']
      genreList = request.form.getlist('genres')
      myArtist.genres=np.array(genreList)
      myArtist.facebook_link=request.form['facebook_link']
      myArtist.image_link=request.form['image_link']
      myArtist.website_link=request.form['website_link']
      if 'seeking_venue' in request.form.keys() :
        myArtist.seekFlag=True
      else:
        myArtist.seekFlag=False

      myArtist.seekAd=request.form['seeking_description']
      db.session.add(myArtist)
      db.session.commit()

  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Artist ' + request.form['name'] + ' failed to be listed!')
        #abort(400)
      else:
         flash('Artist ' + request.form['name'] + ' was successfully listed!')
      # STILL: modify data to be the data object returned from db insertion
      # on successful db insert, flash success
      return render_template('pages/home.html', data=myArtist)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  showList = Shows.query.order_by('id').all()

  class ShowStruct:
    def __init__(self, venue_id, venue_name, artist_id, artist_name, artist_image_link, start_time):
      self.dict = {
        "venue_id": venue_id,
        "venue_name": venue_name,
        "artist_id": artist_id,
        "artist_name": artist_name,
        "artist_image_link": artist_image_link,
        "start_time": start_time.strftime("%Y/%m/%d, %H:%M:%S")
      }

  data = []
  for curShow in showList:
    tempVenue = Venue.query.get(curShow.venue_id)
    tempArtist = Artist.query.get(curShow.artist_id)
    showObj = ShowStruct(curShow.venue_id, tempVenue.name, curShow.artist_id, tempArtist.name, tempArtist.image_link, curShow.time)
    data.append(showObj.dict)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False
  try:
      myShow = Shows()
      myShow.artist_id = request.form['artist_id']
      myShow.venue_id = request.form['venue_id']
      myShow.time = request.form['start_time']
      db.session.add(myShow)
      db.session.commit()
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
        flash('Error: Show failed to be listed!')
        #abort(400)
      else:
        flash('Show was successfully listed!')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:

if __name__ == '__main__':
    app.debug = True #debug mode
    app.run()


# Or specify port manually:

'''
if __name__ == '__main__':
    app.debug = True #debug mode
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

