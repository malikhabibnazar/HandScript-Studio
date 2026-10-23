# HandScript Studio — how to run it

HandScript Studio makes printable cards and envelopes from your templates and handwriting. Everything runs on this computer. You do not need an account, and you do not install Python or Node.

You only install Docker Desktop once. After that, starting and stopping the app is a double-click.

## One-time setup

1. Install **Docker Desktop** for Windows from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
2. Open **Docker Desktop** and wait until it says Docker is running. The first time, Windows may ask you to restart.
3. Leave the HandScript Studio folder where it is. The Start and Stop files must stay in that folder.

## Every time you want to use it

1. Open **Docker Desktop** if it is not already running. Wait until it says Docker is running.
2. Double-click **Start HandScript Studio**.
3. Leave that window open until it says the app is ready. The first start downloads the app and can take a long time. Later starts are much faster.
4. Your browser opens **http://localhost:3000**. That is HandScript Studio. You can also type that address yourself.

You can close the black window after it says the app is ready. The app keeps running.

## When you are finished

1. Double-click **Stop HandScript Studio**.
2. Wait until it says the app is stopped.

Your cards, templates, and files stay on this computer. The next time you double-click Start, they are still there.

## If the page does not open

1. Open **Docker Desktop** and wait until it says Docker is running.
2. Double-click **Start HandScript Studio** again.
3. When the window says the app is ready, open **http://localhost:3000** and refresh the page.

If the Start window shows an error, leave it open and send a photo of that window.

## Good to know

- Use the app only through **http://localhost:3000**.
- The first start needs an internet connection and several gigabytes of free disk space.
- Keep the project folder. Moving or renaming it is fine as long as **Start HandScript Studio** and **Stop HandScript Studio** stay next to the other project files.
- To stop the app, use **Stop HandScript Studio**. That keeps your work. Do not delete Docker’s data from Docker Desktop unless you mean to erase the studio.
