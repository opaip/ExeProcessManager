# ExeProcessManager
a useful ExeProcess manager / [still woking on it]

# Features
* start
* stop
* restart
* loging
* monitoring
* gracefull shutdown

when you want to control a exe file and restart or stop it after an event
for example restat a exe file after a config.json updated


# uagae example
```python
from ExeProcessManager import *
if __name__ == "__main__":
    email_settings = {
        "enabled": True,
        "sender_email": "your_email@example.com",
        "receiver_email": "receiver_email@example.com",
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "smtp_password": "your_email_password"
    }

    manager = ExeProcessManager("your_program.exe", email_config=email_settings)
    manager.auto_restart()
    manager.monitor_resource_usage()
```
