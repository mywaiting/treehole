/*! (c) mywaiting */

const domcontent_loaded_callbacks = []
const on_domcontent_loaded = callback => {
    if (document.readyState === 'loading') {
        if (!domcontent_loaded_callbacks.length) {
            document.addEventListener('DOMContentLoaded', () => {
                for (const callback of domcontent_loaded_callbacks) {
                    callback()
                }
            })
        }
        domcontent_loaded_callbacks.push(callback)
    } else {
        callback()
    }
}


// new_comment
const new_comment = (btn = "new-comment") => {
    document.getElementById(btn).addEventListener("click", event => {
        const url = document.querySelector(".post .user a").getAttribute("href")
        window.open(url)
    })
}
on_domcontent_loaded(new_comment)


// sort_comments
const sort_comments = (selector = ".comments", order = "asc") => {
    const element = document.querySelector(selector)
    const comments = Array.from(element.children)
    const sorted = comments.sort((a, b) => {
        const aid = parseInt(a.id.replace("comment-", ""), 10)
        const bid = parseInt(b.id.replace("comment-", ""), 10)
        return order === "asc" ? aid - bid : bid - aid
    })
    // 用 fragment 批量插入，减少重绘重排
    const fragment = document.createDocumentFragment()
    sorted.forEach(comment => fragment.appendChild(comment))
    element.appendChild(fragment)
}
const sort_comments_oldest_first = (btn = "oldest-first") => {
    document.getElementById(btn).addEventListener("click", event => {
        sort_comments(".comments", "asc")
    })
}
const sort_comments_newest_first = (btn = "newest-first") => {
    document.getElementById(btn).addEventListener("click", event => {
        sort_comments(".comments", "desc")
    })
}
on_domcontent_loaded(sort_comments_oldest_first)
on_domcontent_loaded(sort_comments_newest_first)


// new_reaction
const new_reaction = (btn = "new-reaction") => {
    document.getElementById(btn).addEventListener("click", event => {
        const url = document.querySelector(".post .user a").getAttribute("href")
        window.open(url)
    })
}
on_domcontent_loaded(new_reaction)

