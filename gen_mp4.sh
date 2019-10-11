ffmpeg -y -r 10 -f image2 -i $1/%06d.png -vcodec libx264 -crf 25  -pix_fmt yuv420p -vf pad="width=ceil(iw/2)*2:height=ceil(ih/2)*2" $2

