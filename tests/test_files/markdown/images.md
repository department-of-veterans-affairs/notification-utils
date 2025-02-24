# Images should be removed

## Inline images

![alt text](https://www.example.com/test.png)

![alt text](https://www.example.com/test.jpg "title text")

text before ![alt text](https://www.example.com/test.jpeg) text after

text before ![alt text](https://www.example.com/test.webm "title text") text after

## Reference images

The reference is immediately after the image.

![alt text][image1]
[image1]: https://www.example.com/test.gif

![alt text][image2]
[image2]: https://www.example.com/test.svg "title text"

text before ![alt text][image3] text after
text before [image3]: https://www.example.com/test.tga

text before ![alt text][image4] text after
[image4]: https://www.example.com/test.png "title text"

The reference is not immediately after the image.

![alt text][image5]
![alt text][image6]
text before ![alt text][image7] text after
text before ![alt text][image8] text after

This line separates the images from their references.

[image5]: https://www.example.com/test.png
[image6]: https://www.example.com/test.png "title text"
[image7]: https://www.example.com/test.png
[image8]: https://www.example.com/test.png "title text"
