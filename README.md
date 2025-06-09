# openValves
This project creates a Raspberry Pi based sprinkler system.

The initial roadmap for this project is as follows:
1.  Control existing sprinkler valves with a Raspberry Pi.
    There is an arduino based controller that is currently used to control the valves. The existing circuitry will be swapped onto a raspberry pi and controlled remotely through a ssh connection on a private LAN network.
2.  Create a local web interface to control the valves.  Initially use Django for this.
3.  Create scheduler to turn valves on and off at set times throughout the week.
4.  Create a web scraper that will parse the weather and adjust the watering schedule accordingly.
5.  Create a pi-based shield to make the circuitry more compact and easier to replicate.
6.  Create a manifold that will allow for multiple sub-zones to be more precisely controlled in the garden.
    a.  Mechanical enclosure valves and piping
    b.  Electrical controlling circuity
    c.  Software interface for controlling the sub-zones

Setup:
1.  Start with a freshly installed Raspbian image on a raspberry pi 4 or better.  Get it connected to wifi (needed for upgrades and software installations)
2.  Install the following packages:
    a.  sudo apt update
    b.  sudo apt upgrade
    c.  sudo apt-get install python3-pip
    d.  sudo apt install gh git
    e.  gh auth login
    f.  gh repo clone 'user'/openValves
    g.  cd openValves
    h.  python3 -m venv venv
    i.  source venv/bin/activate
    j.  pip install -r requirements.txt
    k.  sudo apt intstall chromium-browser
3.  Add the python script to CRON
    a.  crontab -e
    b.  Add this line to the cron file.
        0 6 * * * /home/pi/openValves/run_irrigation.sh

    

    
