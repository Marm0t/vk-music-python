# vk-music-python
Simple python script to download all music files from one particular [vk.com](http://vk.com) user.

Before use you must update the following variables in vk-music.py:
* USERNAME - you username/email/phone number to login to vk.com
* PASSWORD - you pasword

Script is using HTMLParser to simulate browser behavior to be able to do OAuth authentification without additional interactions with user.

After execution and successfull login to vk.co script will ask you for user id. You can provide id of any vk.com user to download his/her musicfiles from their "My Music" section.

Note that you cannot access music of users who don't allow you to see their audiofiles in privacy settings.

Have a good day!
