# Discord DnD initiative bot.

Automatically figures out initiative order for DND in conjunction with the Beyond20 Discord
integration.

## Instructions for players

* Claim your character by issuing the following command in the Discord channel:
```
    /initiative I am {CHARACTER_NAME}
```
    * Use at least your character's first name as it appears in discord
    * This is important so that your character isn't treated as an NPC
    * You can update your roll to handle advantage/disadvantage (see below)
* Wait until initiative bot tells everyone to roll for initiative
* Roll for initiative on your character sheet

### What if I rolled without advantage or disadvantage but I was supposed to?
Easy! Just issue either command:
```
    /initiative advantage
```
or
```
    /initiative disadvantage
```
and roll again.

### What if I rolled with advantage or disadvantage but I was supposed to?
Easy! Just issue the command:
```
    /initiative normal
```
This will pick the first roll that was issued.

### What if I rolled with advantage and it was supposed to be disadvantage? Or vice versa?
You can always switch back and forth with repeated calls to
```
    /initiative advantage
```
and
```
    /initiative disadvantage
```
and
```
    /initiative normal
```

As long as 2 rolls have been issued, it will update to the correct value.


## Instructions for DM

To become admin, issue the command:
```
    /initiative
```
The bot will ask if you're the admin. Answer with:
```
    /initiative yes
```

Once you are the admin, request that everyone rolls by:
```
    /initiative
```

Once everyone has rolled (including any NPCs), issue this command:
```
    /initiative get
```

The bot will generate a summary of the initiative order.
