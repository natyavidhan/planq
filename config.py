import os

CONFIG = {
    'google': {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
        'token_url': 'https://accounts.google.com/o/oauth2/token',
        'userinfo': {
            'url': 'https://www.googleapis.com/oauth2/v3/userinfo',
            'email': lambda json: json['email'],
        },
        'scopes': ['https://www.googleapis.com/auth/userinfo.email'],
    },
    'discord': {
        'client_id': os.environ.get('DISCORD_CLIENT_ID'),
        'client_secret': os.environ.get('DISCORD_CLIENT_SECRET'),
        'authorize_url': 'https://discord.com/oauth2/authorize',
        'token_url': 'https://discord.com/api/oauth2/token',
        'userinfo': {
            'url': 'https://discord.com/api/v10/users/@me',
            'email': lambda json: json['email'],
        },
        'scopes': ['email'],
    },
}