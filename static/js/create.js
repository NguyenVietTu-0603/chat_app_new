document.addEventListener('DOMContentLoaded', () => {
    const postMediaInput = document.getElementById('post-media');
    const fileNameDisplay = document.getElementById('file-name');
    const mediaSlides = document.getElementById('media-slides');
    const mediaDots = document.getElementById('media-dots');
    const postPreview = document.querySelector('.post-preview');
    const createPostForm = document.getElementById('create-post-form');

    if (postMediaInput) {
        postMediaInput.addEventListener('change', function (event) {
            const files = event.target.files;

            if (files.length > 0) {
                postPreview.style.display = 'block';
                fileNameDisplay.textContent = `${files.length} tệp đã được thêm`;

                Array.from(files).forEach((file, index) => {
                    const fileURL = URL.createObjectURL(file);

                    if (file.type.startsWith('image/')) {
                        const img = document.createElement('img');
                        img.src = fileURL;
                        mediaSlides.appendChild(img);
                    } else if (file.type.startsWith('video/')) {
                        const video = document.createElement('video');
                        video.src = fileURL;
                        video.controls = true;
                        mediaSlides.appendChild(video);
                    }

                    const dot = document.createElement('div');
                    dot.classList.add('dot');
                    dot.dataset.index = mediaDots.children.length;
                    mediaDots.appendChild(dot);
                });

                initializeSlider();
                event.target.value = '';
            } else {
                postPreview.style.display = 'none';
                fileNameDisplay.textContent = "Chưa chọn tệp nào";
            }
        });
    }

    function initializeSlider() {
        let index = 0;
        const slides = document.querySelector(".slides");
        const items = slides.children;
        const dots = document.querySelectorAll(".dot");

        function updateSlide() {
            slides.style.transform = `translateX(${-index * 100}%)`;
            dots.forEach(dot => dot.classList.remove("active"));
            dots[index].classList.add("active");
        }

        const leftZone = document.createElement("div");
        leftZone.classList.add("click-zone", "left");
        const rightZone = document.createElement("div");
        rightZone.classList.add("click-zone", "right");

        leftZone.addEventListener("click", () => {
            index = (index - 1 + items.length) % items.length;
            updateSlide();
        });

        rightZone.addEventListener("click", () => {
            index = (index + 1) % items.length;
            updateSlide();
        });

        const slider = document.querySelector(".slider");
        slider.appendChild(leftZone);
        slider.appendChild(rightZone);

        dots.forEach(dot => {
            dot.addEventListener("click", () => {
                index = parseInt(dot.dataset.index);
                updateSlide();
            });
        });

        if (dots.length > 0) dots[0].classList.add("active");
    }
});
