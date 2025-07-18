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
    document.getElementById(bnt).addEventListener("click", event => {
        
    })
}
on_domcontent_loaded(new_comment)


// sort_comments
const sort_comments = (selector = "comment", sorted = "oldest") => {

}
const sort_comments_oldest_first = (btn = "oldest-first") {
    document.getElementById(bnt).addEventListener("click", event => {

    })
}
const sort_comments_newest_first = (btn = "newest-first") {
    document.getElementById(bnt).addEventListener("click", event => {

    })
}
on_domcontent_loaded(sort_comments_oldest_first)
on_domcontent_loaded(sort_comments_newest_first)


// new_reaction
const new_reaction = (btn = "new_reaction") => {
    document.getElementById(bnt).addEventListener("click", event => {

    })
}
on_domcontent_loaded(new_reaction)

