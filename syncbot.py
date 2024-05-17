import requests
import sys
import json
import discord
from discord import Client
import asyncio


#if 'trello' in cfg:
#    trello = cfg['trello']
#    board_id = trello['board_id'] 
#    trello_key = trello['api_key'] #open('./trello_apikey.txt').read().strip()
#    trello_token = trello['token'] #open('./trello_token.txt').read().strip()
#    trello_landing_zone = trello['landing_zone'] # 
#    trello_creds={'key':trello_key,'token':trello_token}
#else:
#    print("No trello config, this was probably a good choice!")

# cfg example
# {"discourse": {"cookie" : {dict of your cookies from a logged in session}},
#  "discord": {"token":"yourtoken", "server_id":"1234", "landing_zone":"1234"}}
#

cfg = json.loads(open(sys.argv[1]).read())
if 'discourse' in cfg:
    discourse_url = cfg['discourse']['url']
    discourse_cookies = cfg['discourse']['cookies']
else:
    print("No discourse cookie! This won't work without it!")
    sys.exit(1)

if 'discord' in cfg:
    disc = cfg['discord']
    discord_token =  disc['token']

    discord_server_id = disc['server_id'] 
    discord_landing_zone = disc['landing_zone'] # This is the ID of the category to post in 
else:
    print("No discord creds! This won't with without them!")
    sys.exit(1)
    
def get_chal(post_id):
    req = discourse_url+'/t/'+str(post_id)+'.json'
    res = requests.get(req, cookies=discourse_cookies, verify='./ca.crt')
    data = res.json()
    posts = data['post_stream']['posts']
    post_texts = []
    for post in posts:
        req2 = discourse_url+'/posts/'+str(post['id'])+'.json'
        res2 = requests.get(req2, cookies=discourse_cookies,verify='./ca.crt')
        post_text = res2.json()['raw']
        post_user = res2.json()['display_username']
        post_texts.append(post_user+':'+ post_text+'\n=====\n')
    return post_texts

def get_challenges():
    req = discourse_url + '/latest.json'
    res = requests.get(req, cookies=discourse_cookies, verify='./ca.crt')
    data = res.json()
    #print(data)
    posts = data['topic_list']['topics']
    posts_dict = {post['id']:post for post in posts}
    return posts_dict


# This gets called from inside the discord async stuff because it was the easiest way to get that result out.
async def compare_all(discord_state, homeserver):

    #cards = get_cards()
    challenges = get_challenges()
    landing_category = None
    for c in homeserver.categories:
        if str(c.id) == discord_landing_zone:
            landing_category = c
    for challenge in challenges:
        title = challenges[challenge]['title']
        url = discourse_url+'/t/'+challenges[challenge]['slug']+'/'+str(challenge)
        post_texts = get_chal(str(challenge))
        challenge = str(challenge)
        #if challenge not in cards:
        #    print('Challenge:'+challenge+' is not on Trello')
        #    make_card(title, challenge)
        print("Checking:", challenge, title)
        if challenge not in discord_state:
            print('Challenge:'+challenge+' is not in Discord')
            channel = await landing_category.create_text_channel(title, topic='CHALLENGEID:'+challenge)
            await channel.send(url)
            for text in post_texts:
                await channel.send(text)
        if 0: 
            for message in discord_state[challenge][1]:
                found=False
                for text in post_texts:
                    if message.content == text:
                        found=True
                if not found:
                    print(message.content, 'was not found')


client = discord.Client()
@client.event
async def on_ready():
    async def get_bot_posts(channel):
        seen = []
        async for message in channel.history():
            if message.author == client.user:
                seen.append(message)
        return seen


    print('We have logged in as {0.user}'.format(client))
    state = {}
    for server in client.guilds:
        if str(server.id) != discord_server_id:
            continue
        homeserver = server
        for channel in server.channels:
            if channel.type == discord.ChannelType.text:
                if channel.topic is not None and 'CHALLENGEID' in channel.topic:
                    discourse_challenge = channel.topic.split('CHALLENGEID:')[1].strip()
                    state[discourse_challenge] = (channel,await get_bot_posts(channel))
    await compare_all(state,homeserver)
    await client.close()


if __name__ == '__main__':
    client.run(discord_token)

async def gather_channels(channels): #TODO see if this can replace the sync for up above in on_ready()
    state = {}
    channels = [x for x in channels if x.type == discord.ChannelType.text and channel.topic is not None and 'CHALLENGEID' in channel.topic]
    channel_challenges = [(x, x.topic.split('CHALLENGEID:')[1].strip()) for x in channels]
    results = asyncio.gather(*[(chid,get_bot_posts(x)) for ch,chid in channel_challenges])
    async for (chid, result) in results:
        state[chid] = result
    return state

