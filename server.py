from flask import Flask, Markup, render_template, request
import pymysql
import time
import os


current_tournament_id = 2912

clean = str.maketrans('', '', """ ^$#@~`&;:|{()}[]<>+=!?.,\/*-_"'""")
sanitize = str.maketrans('', '', """^~`;:|{()}[]+=\*_"'""")

#Configuration
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
db_ip = os.environ['DB_IP']

# Open database connection
db = pymysql.connect(db_ip, db_user, db_password, db_name)
c = db.cursor()


def report(team_name, auton_score, driver_score, highest_stack, reporter_ip, notes=""):
    time_stamp = int(time.time())
    c.execute('INSERT INTO Reports(team_name, auton_score, driver_score, highest_stack, notes, time_stamp, reporter_ip, tournament_id)' +
              'VALUES ("'+team_name+'",'+str(auton_score)+','+str(driver_score)+','+str(highest_stack)+',"'+notes+'",'+str(time_stamp)+','+str(reporter_ip)+','+str(current_tournament_id)+")")
    db.commit()

def pull_reports(tournament_id, team_name=None):
    if team_name:
        c.execute('SELECT * FROM Reports WHERE team_name="' + team_name + '" and tournament_id=' + str(tournament_id))
    else:
        c.execute('SELECT * FROM Reports WHERE tournament_id=' + str(tournament_id))
    return c.fetchall()

def get_unscouted_robots(tournament_id): # Returns a list of unscouted robots in string name form
	scouted = []
	unscouted = []
	for r in pull_reports(tournament_id):
		for t in valid_teams:
			if t == r[0] and t not in scouted:
				scouted.append(t)
	for r in valid_teams:
		if r not in scouted:
			unscouted.append(r)
	return unscouted

def compress_reports(tournament_id): # Compile data and find average values for each robot
    c.execute('SELECT team_name, auton_score, driver_score, highest_stack, notes FROM Reports WHERE tournament_id=' + str(tournament_id))
    robotData = c.fetchall()
    robots = []
    for row in robotData:  # Find unique robots
        if row[0] not in robots: robots.append(row[0])
    compressedData = []
    for robot in robots:
        best_drive_score = 0
        best_auton_score = 0
        total_drive_score = 0
        total_auton_score = 0
        highest_stack = 0
        entryCount = 0
        notes = ''
        for row in robotData:
            if row[0] == robot:
                entryCount += 1
                total_drive_score += int(row[2])
                total_auton_score += int(row[1])
                if int(row[2]) > best_drive_score:
                	best_drive_score = int(row[2])
                if int(row[1]) > best_auton_score:
                	best_auton_score = int(row[1])
                if int(row[3]) > highest_stack:
                	highest_stack = int(row[3])
                if row[4]:
                	notes += '~ '+row[4]+'<br>'
        compressedData.append([robot, best_drive_score, int(total_drive_score / entryCount), best_auton_score, int(total_auton_score / entryCount), highest_stack, notes, entryCount])
    return compressedData


def robot_power(robot_stats): # Enter compiled data row as input. Formula: power = best_driver + avg_driver + best_auton + avg_auton + highest_stack * 2 + times_scouted
	return robot_stats[1] + robot_stats[2] + robot_stats[3] + robot_stats[4] + robot_stats[5] * 2 + robot_stats[7]


def reverse_bubble_sort(collection): # Sort reports by best robot power
	length = len(collection)
	for i in range(length-1, -1, -1):
		for j in range(i):
			if robot_power(collection[j]) > robot_power(collection[j+1]):
				collection[j], collection[j+1] = collection[j+1], collection[j]
	return collection[::-1]


app = Flask(__name__)

@app.route('/') # Home page
def index():
	c.execute('SELECT tournament_name FROM Tournaments WHERE tournament_id=' + str(current_tournament_id))
	tournament_name = c.fetchall()[0][0]
	return render_template('index.html', current_tournament_name=tournament_name, current_tournament_id=current_tournament_id, status="Seaquam Robotics Scouting")

@app.route('/scouting', methods=['POST', 'GET']) # Scouting submission page
def scouting():
	error = None
	if request.method == 'POST':
		auton_score = 0
		score = 0
		team_name = request.form['team'].translate(clean).upper()
		if team_name in valid_teams:
			print("Report submitted for " + team_name)
			#Autonomous
			if request.form['auton_mobile_goal'] == "far":
				auton_score = 20
			elif request.form['auton_mobile_goal'] == "mid":
				auton_score = 10
			elif request.form['auton_mobile_goal'] == "near":
				auton_score = 5
			auton_score += int(request.form['auton_cones_stacked']) * 2
			
			if int(request.form['driver_num_mobile_mid']) + int(request.form['driver_num_mobile_near']) + (request.form.get('driver_is_mobile_far') == "yes") > 4:
				return render_template('index.html', status=Markup('<span class="error">Error:</span> Too many mobile goals submitted. Only 4 exist.'))

			#Driver/Total
			if request.form.get('driver_is_mobile_far') == "yes":
				score += 20 + int(request.form['driver_num_cones_far']) * 2
			score += int(request.form['driver_num_mobile_mid']) * 10 + int(request.form['driver_num_cones_mid']) * 2
			score += int(request.form['driver_num_mobile_near']) * 5 + int(request.form['driver_num_cones_near']) * 2
			score += int(request.form['driver_num_cones_tower']) * 2

			highest_stack = request.form['driver_highest_stack']
			reporter_ip = request.environ['REMOTE_ADDR'].translate(clean)

			#team_name, auton_score, driver_score, highest_stack, reporter_ip, notes=""

			report(team_name, auton_score, score, highest_stack, reporter_ip, request.form['notes'].translate(sanitize))
		else:
			if len(team_name) == 0:
				team_name = "NULL"
			return render_template('index.html', status=Markup('<span class="error">Error:</span> Invalid team name: ' + team_name + " not found in list of participating robots."))
		return render_template('index.html', status="Scouting report sent successfully")
	elif request.method == 'GET':
		return render_template('scouting.html', error=error)

@app.route('/data/<int:tournament_id>') # Compiled scouting reports page
def data(tournament_id):
	c.execute('SELECT tournament_name FROM Tournaments WHERE tournament_id=' + str(tournament_id))
	tournament_name = c.fetchall()[0][0]
	robots_data = ''
	for i, row in enumerate(reverse_bubble_sort(compress_reports(tournament_id))):
		robots_data += '<tr><td>'+str(i+1)+'</td>'
		for cell in row:
			robots_data += '<td>'+str(cell)+'</td>'
		robots_data +='</tr>'
	robots_data_html = Markup(robots_data)

	unscouted_robots = get_unscouted_robots(tournament_id)
	unscouted = ''
	if unscouted_robots:
		unscouted += '<h2>Not Yet Scouted:</h2><div class="unscouted">'
	else:
		unscouted = '<h2>All Robots Scouted</h2>'
	for r in unscouted_robots:
		unscouted += r+' '
	unscouted_html = Markup(unscouted+'</div>')

	return render_template('data.html', tournament_name=tournament_name, data=robots_data_html, unscouted=unscouted_html)

@app.route('/past-tournaments')
def past_tournaments():
	tournaments_html = ''
	c.execute('SELECT tournament_id, tournament_name, team_list FROM Tournaments')
	for t in c.fetchall():
		tournaments_html += '<a class="box2" href="data/' + str(t[0]) + '">' + t[1] + '</a>'
	tournaments_html = Markup(tournaments_html)
	return render_template('past_tournaments.html', tournaments=tournaments_html)

@app.route('/agenda')
def agenda():
	return render_template('agenda.html')

@app.errorhandler(404) #Error 404 page
def page_not_found(e):
	return render_template('404.html'), 404

if __name__ == '__main__':

	# Create tables if they do not already exist
	c.execute('SHOW TABLES')
	tbls = str(c.fetchall())
	if 'Tournaments' not in tbls:
		c.execute('CREATE TABLE IF NOT EXISTS Tournaments(tournament_id INT, tournament_name TEXT, team_list TEXT, PRIMARY KEY (tournament_id))')
	if 'Reports' not in tbls:
		c.execute('CREATE TABLE IF NOT EXISTS Reports(team_name TEXT, auton_score INT, driver_score INT, highest_stack INT, notes TEXT, time_stamp BIGINT, reporter_ip BIGINT, tournament_id INT)')
	
	c.execute('SELECT team_list FROM Tournaments WHERE tournament_id=' + str(current_tournament_id))
	valid_teams = c.fetchall()
	valid_teams = valid_teams[0][0].split()

	app.run(threaded=True, debug=True, host='0.0.0.0', port=8000)

db.close()
